from flask import request, Flask
from flask_cors import CORS
from qiskit import IBMQ, transpile, Aer, execute
from collections import defaultdict
from qiskit.test.mock import FakeProvider
import io, base64, re, json

app = Flask(__name__)
CORS(app)

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

    configs = backend.configuration()
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

DEFAULT_ERRORS = {
  'cx': 1.327e-2, 
  'sx': 3.770e-4, 
  'x': 3.770e-4
}

def calc_error(ops_dict, error_dict=DEFAULT_ERRORS):
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
def toQasm():
    try:
        loc = {}
        js = request.get_json()
        exec(js['code'].replace("\\n", "\n"), {}, loc)
        return {"code": str(loc['qc'].qasm())}
    except Exception as e:
        return str(e), 400

@app.route("/qiskit_draw", methods=["POST"])
def qiskit_draw():
    try:
        loc = {}
        js = request.get_json()
        exec(js['code'].replace("\\n", "\n"), {}, loc)
        return {"pic": mpl2base64(loc['qc'].draw('mpl'))}
    except Exception as e:
        return str(e), 400

@app.route("/recommend", methods=["POST"])
def rec():
    try:
        loc = {}
        js = request.get_json()
        exec(js['code'].replace("\\n", "\n"), {}, loc)
        backend = FakeProvider().get_backend("fake_"+js.get('system'))
        layouts = ['noise_adaptive', 'dense', 'trivial']
        routings = ['stochastic', 'basic']
        schedulings = [None, 'as_soon_as_possible', 'as_late_as_possible']
        optlvls = range(4)
        gates_errors = get_errors(backend)
        res = []
        for layout in layouts:
            for routing in routings:
                for optlvl in optlvls:
                    for scheduling in schedulings:
                        qcAmount = {}
                        gateWithAmount = {}
                        qcTrans = transpile(loc['qc'], backend=backend, layout_method=layout, routing_method=routing, scheduling_method=scheduling, optimization_level=optlvl)
                        for name, amount in qcTrans.count_ops().items():
                            qcAmount[name] = amount
                        for name, _ in gates_errors.items():
                            if name not in ['id', 'reset']:
                                gateWithAmount[name] = qcAmount.get(name, 0)
                        acc_err = calc_error(gateWithAmount, gates_errors)
                        res.append({'optlvl': optlvl, 'layout': layout, 'routing': routing, 'scheduling': scheduling, 'acc_err': acc_err/100})
        res = sorted(res, key = lambda i: i['acc_err'])
        return json.dumps(res)
    except Exception as e:
        return str(e), 400

@app.route("/simulation", methods=["POST"])
def simu():
    try:
        loc = {}
        js = request.get_json()
        exec(js['code'].replace("\\n", "\n"), {}, loc)
        backend = Aer.get_backend(js.get('system'))
        shots = js.get('shots')
        result = execute(loc['qc'], backend, shots=shots).result()
        return {"probability": result.get_counts()}
    except Exception as e:
        return str(e), 400

@app.route("/transpile", methods=["POST"])
def trans():
    try:
        loc = {}
        js = request.get_json()
        exec(js['code'].replace("\\n", "\n"), {}, loc)
        backend = FakeProvider().get_backend("fake_"+js.get('system'))
        layout = js.get('layout')
        routing = js.get('routing')
        scheduling = js.get('scheduling')
        optlvl = js.get('optlvl')
        qcTrans = transpile(loc['qc'], backend=backend, layout_method=layout, routing_method=routing, scheduling_method=scheduling, optimization_level=optlvl)
        return {"pic": mpl2base64(qcTrans.draw('mpl', idle_wires=False, fold=-1))}
    except Exception as e:
        return str(e), 400

@app.route("/setAccount", methods=["POST"])
def setAcc():
    try:
        js = request.get_json()
        if IBMQ.active_account() == None or js.get("api_key") != IBMQ.active_account().get("token"):
            print(IBMQ.save_account(js.get("api_key"), overwrite=True))
        IBMQ.load_account()
        return {"message": "Set account successfully."}
    except Exception as e:
        return str(e), 400

@app.route("/getAccount", methods=["GET"])
def getAcc():
    try:
        return {"message": IBMQ.active_account()}
    except Exception as e:
        return str(e), 400

@app.route("/deleteAccount", methods=["POST"])
def delAcc():
    try:
        js = request.get_json()
        if IBMQ.active_account() == None:
            msg = "No active account."
            code = 401
        elif IBMQ.active_account().get('token') != js.get('api_key'):
            msg = "Token not match."
            code = 401
        else:
            IBMQ.disable_account()
            IBMQ.delete_account()
            msg = "Delete successfully."
            code = 200
        return {"message": msg}, code
    except Exception as e:
        return str(e), 400

if __name__ == "__main__":
    app.run(debug=True)