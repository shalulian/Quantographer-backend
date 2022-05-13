import json
import time

from datetime import datetime, timezone

from flask import Flask, request
from flask_cors import CORS
from flask_sock import Sock

from qiskit import transpile, execute
from qiskit.providers.aer.aerprovider import AerProvider
from qiskit.providers.ibmq import IBMQFactory

from util import get_available_backends, get_errors, calc_error, plot_png, to_data_url

app = Flask(__name__)
sock = Sock(app)

CORS(app)

CHOSEN_PARAMETERS = [
    ('noise_adaptive', 'stochastic'),
    ('noise_adaptive', 'basic'),
    ('trivial', 'basic')
]

def wrap_response(func):
    # wrapper function
    def inner(*args, **kwargs):
        try:
            # get result
            res = func(*args, **kwargs)

            # wrap in structure
            pack = {
                'status': 'ok',
                'result': res
            }

            return pack, 200

        except Exception as e:
            # wrap error in structure
            err = {
                'status': 'error',
                'error': type(e).__name__
            }

            return err, 400

    # preserve old name
    inner.__name__ = func.__name__

    return inner

def wrap_ws(func):
    # wrapper function
    def inner(ws, *args, **kwargs):
        try:
            # get result
            func(ws, *args, **kwargs)

        except Exception as e:
            # wrap error in structure
            err_packet = json.dumps(
                {
                    'status': 'ERROR',
                    'error': type(e).__name__
                }
            )

            ws.send(err_packet)
            ws.close()

            raise

    # preserve old name
    inner.__name__ = func.__name__

    return inner

def exec_circuit(code):
    glob = {}
    loc = {}

    exec(code, glob, loc)

    return loc['qc']


@app.route('/convert_qasm', methods=['POST'])
@wrap_response
def convert_qasm():
    req = request.get_json()
    code = req['code']

    circuit = exec_circuit(code)
    asm = circuit.qasm()

    return f'{asm}'

@app.route('/convert_image', methods=['POST'])
@wrap_response
def convert_image():
    req = request.get_json()
    code = req['code']

    circuit = exec_circuit(code)
    plot = circuit.draw('mpl')

    png_bytes = plot_png(plot)

    return to_data_url('image/png', png_bytes)

@app.route('/run_simulation', methods=['POST'])
@wrap_response
def run_simulation():
    req = request.get_json()

    code = req['code']
    system = req['system']
    shots = req.get('shots', 1024)

    circuit = exec_circuit(code)

    Aer = AerProvider()
    backend = Aer.get_backend(system)

    job = execute(circuit, backend, shots=shots)

    res = job.result()
    counts = res.get_counts()

    return counts

@app.route('/transpile', methods=['POST'])
@wrap_response
def transpile_circuit():
    req = request.get_json()

    key = req['key']
    code = req['code']
    system = req['system']
    level = req['level']
    layout = req['layout']
    routing = req['routing']
    scheduling = req['scheduling']

    IBMQ = IBMQFactory()
    provider = IBMQ.enable_account(key)
    backend = provider.get_backend(system)

    circuit = exec_circuit(code)

    transpiled_circuit = transpile(
        circuit,
        backend=backend,
        layout_method=layout,
        routing_method=routing,
        scheduling_method=scheduling,
        optimization_level=level
    )

    plot = transpiled_circuit.draw('mpl', idle_wires=False, fold=-1)
    png_bytes = plot_png(plot)

    return to_data_url('image/png', png_bytes)

@app.route('/available_backend', methods=['POST'])
@wrap_response
def available_backend():
    req = request.get_json()

    key = req['key']

    IBMQ = IBMQFactory()
    provider = IBMQ.enable_account(key)

    backends = get_available_backends(provider)
    res = list(backends)

    return res

@app.route('/recommend', methods=['POST'])
@wrap_response
def recommend_backend():
    req = request.get_json()

    key = req['key']
    code = req['code']

    IBMQ = IBMQFactory()
    provider = IBMQ.enable_account(key)

    circuit = exec_circuit(code)

    res = []

    for backend_brief in get_available_backends(provider, True):
        if circuit.num_qubits > backend_brief['qb']:
            # skip backend that smaller than circuit
            continue

        # get backend object
        backend = backend_brief['backend']
        backend_name = backend_brief['name']

        try:
            gates_errors = get_errors(backend)

        except Exception:
            # skip backend that can't obtain error
            continue

        for layout, routing in CHOSEN_PARAMETERS:
            for level in range(4):
                try:
                    transpiled_circuit = transpile(
                        circuit,
                        backend=backend,
                        layout_method=layout,
                        routing_method=routing,
                        optimization_level=level
                    )
                except:
                    # skip system that produce error during transpile
                    continue

                acc_err = calc_error(transpiled_circuit.count_ops(), gates_errors)

                res.append(
                    {
                        'system': backend_name,
                        'level': level,
                        'layout': layout,
                        'routing': routing,
                        'acc_err': acc_err / 100
                    }
                )

    return res

@sock.route('/run')
@wrap_response
@wrap_ws
def run_backend(ws):
    raw = ws.receive()
    req = json.loads(raw)

    key = req['key']
    code = req['code']
    system = req['system']
    level = req['level']
    layout = req['layout']
    routing = req['routing']
    scheduling = req['scheduling']
    shots = req.get('shots', 1024)

    IBMQ = IBMQFactory()
    provider = IBMQ.enable_account(key)
    backend = provider.get_backend(system)

    circuit = exec_circuit(code)

    transpiled_circuit = transpile(
        circuit,
        backend=backend,
        layout_method=layout,
        routing_method=routing,
        scheduling_method=scheduling,
        optimization_level=level
    )

    job = execute(transpiled_circuit, backend=backend, shots=shots)

    while True:
        # poll status
        status = job.status()

        kind = status.name

        # end status
        if kind in ['DONE', 'CANCELLED', 'ERROR']:
            break

        report = {
            'status': kind
        }

        if kind == 'QUEUED':
            queue_index = job.queue_position()
            queue_info = job.queue_info()

            # calc elapse
            est_time = queue_info.estimated_start_time - datetime.now(timezone.utc)

            # add progress
            report.update(
                {
                    'queue': queue_index,
                    'est_time': str(est_time)
                }
            )

        # serialize data
        raw = json.dumps(report)

        # send data
        ws.send(raw)

        time.sleep(2 if kind == 'RUNNING' else 5)

    result = job.result()

    counts = result.get_counts()
    count_pairs = counts.items()

    ws.send(
        json.dumps(
            {
                'status': kind,
                'value': list(count_pairs)
            }
        )
    )

    ws.close()

if __name__ == '__main__':
    app.run(debug=True)
