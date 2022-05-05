import time
from flask import request, Flask
from flask_cors import CORS
from flask_sock import Sock
from qiskit import IBMQ, transpile, Aer, execute
from collections import defaultdict
from qiskit.test.mock import FakeProvider
import io, base64, re, json

app = Flask(__name__)
CORS(app)
sock = Sock(app)

def mpl2base64(mpl):
    s = io.BytesIO()
    mpl.savefig(s, format='png', bbox_inches="tight")
    s = base64.b64encode(s.getvalue()).decode("utf-8").replace("\n", "")
    return "data:image/png;base64,%s" % s

def get_error(gate):
  for param in gate.parameters:
    if param.name == 'gate_error':
      return param.value
  return 0

def get_errors(backend):
    NAME_EXTRACTOR = re.compile(r'^([a-z]+)(.*)')

    props = backend.properties()

    gates_errors = defaultdict(list)
    for gate in props.gates:
        extract_res = NAME_EXTRACTOR.match(gate.name)
        name, _ = extract_res.groups()
        error = get_error(gate)
        gates_errors[name].append(error)

    for gate, errors in gates_errors.items():
        gates_errors[gate] = sum(errors) / len(errors)

    return gates_errors

def calc_error(ops_dict, error_dict):
  p_not_errors = 1.0
  for gate_name, amount in ops_dict.items():
    try:
      p_err = error_dict[gate_name]
    except:
      # skip unknow error gates
      pass
    else:
      p_not_error = 1.0 - p_err
      p_not_errors *= p_not_error ** amount
  # return 1.0 - p_not_errors
  return (1.0 - p_not_errors)*10000

@app.route("/qasm", methods=["POST"])
def toQasm(get = None):
    try:
        loc = {}
        js = request.get_json() if get == None else get
        exec(js.get('code').replace("\\n", "\n"), {}, loc)
        return {"code": str(loc.get('qc').qasm())} if get == None else str(loc.get('qc').qasm())
    except Exception as e:
        return {"error": str(e)}, 400

@app.route("/qiskit_draw", methods=["POST"])
def qiskit_draw(get = None):
    try:
        loc = {}
        js = request.get_json() if get == None else get
        exec(js.get('code').replace("\\n", "\n"), {}, loc)
        return {"pic": mpl2base64(loc.get('qc').draw('mpl'))} if get == None else mpl2base64(loc.get('qc').draw('mpl'))
    except Exception as e:
        return {"error": str(e)}, 400

@app.route("/simulation", methods=["POST"])
def simu(get = None):
    try:
        loc = {}
        js = request.get_json() if get == None else get
        exec(js.get('code').replace("\\n", "\n"), {}, loc)
        backend = Aer.get_backend(js.get('system'))
        shots = js.get('shots')
        result = execute(loc.get('qc'), backend, shots=shots).result()
        return {"result": result.get_counts()} if get == None else result.get_counts()
    except Exception as e:
        return {"error": str(e)}, 400

@app.route("/recommend", methods=["POST"])
def rec(get = None):
    try:
        loc = {}
        js = request.get_json() if get == None else get
        try:
            if IBMQ.active_account() != None:
                IBMQ.disable_account()
            provider = IBMQ.enable_account(js.get('api_key'))
        except Exception as e:
            return {"error": f"Unauthorized key. Login failed. ({e})"}, 400
        exec(js.get('code').replace("\\n", "\n"), {}, loc)
        layoutsAndRoutings = [{'noise_adaptive', 'stochastic'}, {'noise_adaptive', 'basic'}, {'trivial', 'basic'}]
        optlvls = range(4)
        res = []
        backends = {}
        errs = {}
        for b in provider.backends():
            backends[b] = len(b.properties().qubits) if b.properties() != None else 0
        for layout, routing in layoutsAndRoutings:
            for optlvl in optlvls:
                for backend in backends:
                    if loc.get('qc').num_qubits > backends[backend]:
                        continue
                    gates_errors = get_errors(backend)
                    qcAmount = {}
                    gateWithAmount = {}
                    try:
                        qcTrans = transpile(loc.get('qc'), backend=backend, layout_method=layout, routing_method=routing, optimization_level=optlvl)
                    except Exception as e:
                        errs[str(backend)] = str(e)
                        continue
                    for name, amount in qcTrans.count_ops().items():
                        qcAmount[name] = amount
                    for name, _ in gates_errors.items():
                        if name not in ['id', 'reset']:
                            gateWithAmount[name] = qcAmount.get(name, 0)
                    acc_err = calc_error(gateWithAmount, gates_errors)
                    res.append({'system':str(backend), 'optlvl': optlvl, 'layout': layout, 'routing': routing, 'acc_err': acc_err/100})
        if res == []:
            return errs, 400
        return json.dumps(sorted(res, key = lambda i: i['acc_err'])) if get == None else sorted(res, key = lambda i: i['acc_err'])
    except Exception as e:
        return {"error": str(e)}, 400

@app.route("/transpile", methods=["POST"])
def trans(get = None):
    try:
        loc = {}
        js = request.get_json() if get == None else get
        exec(js.get('code').replace("\\n", "\n"), {}, loc)
        backend = FakeProvider().get_backend("fake_"+js.get('system'))
        layout = js.get('layout')
        routing = js.get('routing')
        scheduling = js.get('scheduling')
        optlvl = js.get('optlvl')
        qcTran = transpile(loc.get('qc'), backend=backend, layout_method=layout, routing_method=routing, scheduling_method=scheduling, optimization_level=optlvl)
        return {"pic": mpl2base64(qcTran.draw('mpl', idle_wires=False, fold=-1))} if get == None else mpl2base64(qcTran.draw('mpl', idle_wires=False, fold=-1))
    except Exception as e:
        return {"error": str(e)}, 400

@app.route("/get_backend", methods=["POST"])
def getBackend(get = None):
    js = request.get_json() if get == None else get
    try:
        # if IBMQ.active_account() == None or IBMQ.active_account().get('token') != js.get('api_key'):
        if IBMQ.active_account() != None:
            IBMQ.disable_account()
        provider = IBMQ.enable_account(js.get('api_key'))
    except:
        return {"error": f"Unauthorized key. Login failed. ({e})"}, 400
    try:
        return {"backend":[str(i) for i in provider.backends()]} if get == None else [str(i) for i in provider.backends()]
    except Exception as e:
        return {"error": str(e)}, 400

@sock.route("/run")
def runOnReal(ws):
    # js = request.get_json()
    try:
        js = json.loads(ws.receive())
        if IBMQ.active_account() != None:
            IBMQ.disable_account()
        provider = IBMQ.enable_account(js.get('api_key'))
        print("logined")
    except Exception as e:
        ws.send({"error": f"Unauthorized key. Login failed. ({e})", "status": "ERROR"})
        ws.close()
        return {"error": f"Unauthorized key. Login failed. ({e})"}, 400
    try:
        loc = {}
        print("code")
        exec(js.get('code').replace("\\n", "\n"), {}, loc)
        print("get backend")
        device = provider.get_backend(js.get('system'))
        print("transpile")
        qcTran = transpile(loc.get('qc'), backend=device, layout_method=js.get('layout'), routing_method=js.get('routing'), scheduling_method=js.get('scheduling'), optimization_level=js.get('optlvl'))
        print("execute")
        job = execute(qcTran, backend=device,shots=js.get('shots', 1000))
        print("executed")
        status = job.status()
        while status.name not in ["DONE", "CANCELLED", "ERROR"]:
            print(status.name)
            msg = {"status": status.name}
            if status.name == "QUEUED":
                msg["queue"] = job.queue_position()
            ws.send(msg)
            if status.name == "RUNNING":
                time.sleep(2)
            else:
                time.sleep(5)
            status = job.status()
        print("get result")
        device_result = job.result()
        print("print result")
        ws.send({"status": job.status().name, "value": device_result.get_counts(loc.get('qc'))})
        print("end")
        ws.close()
    except Exception as e:
        ws.send({"error": str(e), "status": "ERROR"})
        ws.close()
        return {"error": str(e)}, 400

if __name__ == "__main__":
    app.run(debug=True)