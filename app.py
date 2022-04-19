from flask import request, Flask
from flask_cors import CORS
from qiskit import IBMQ, transpile, Aer, execute
import io
import base64

app = Flask(__name__)
CORS(app)

def mpl2base64(mpl):
    s = io.BytesIO()
    mpl.savefig(s, format='png', bbox_inches="tight")
    s = base64.b64encode(s.getvalue()).decode("utf-8").replace("\n", "")
    return "data:image/png;base64,%s" % s

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

@app.route("/simulation", methods=["POST"])
def simu():
    try:
        loc = {}
        js = request.get_json()
        exec(js['code'].replace("\\n", "\n"), {}, loc)
        backend = Aer.get_backend(js.get('backend'))
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
        backend = js.get('backend')
        layout_method = js.get('layout_method')
        routing_method = js.get('routing_method')
        scheduling_method = js.get('scheduling_method')
        basis_gates = ['u1', 'u2', 'u3', 'cx'] if backend == None else js.get('basis_gates')
        qcTrans = transpile(loc['qc'], backend=backend, layout_method=layout_method, routing_method=routing_method, scheduling_method=scheduling_method, basis_gates=basis_gates)
        return {"pic": mpl2base64(qcTrans.draw('mpl'))}
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