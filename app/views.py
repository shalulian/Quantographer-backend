from app import app
from flask import request
from qiskit import IBMQ, transpile, Aer, execute

@app.route("/qasm", methods=["POST"])
def toQasm():
    js = request.get_json()
    exec(js['code'].replace("\\n", "\n"), globals())
    return {"code": str(qc.qasm())}

@app.route("/qiskit_draw", methods=["POST"])
def qiskit_draw():
    js = request.get_json()
    exec(js['code'].replace("\\n", "\n"), globals())
    return {"code": qc.draw('mpl')}

@app.route("/simulation", methods=["POST"])
def simu():
    js = request.get_json()
    exec(js['code'].replace("\\n", "\n"), globals())
    backend = Aer.get_backend(js.get('backend'))
    shots = js.get('shots')
    result = execute(qc, backend, shots=shots).result()
    return {"probability": result.get_counts()}

@app.route("/transpile", methods=["POST"])
def trans():
    js = request.get_json()
    exec(js['code'].replace("\\n", "\n"), globals())
    backend = js.get('backend')
    layout_method = js.get('layout_method')
    routing_method = js.get('routing_method')
    scheduling_method = js.get('scheduling_method')
    basis_gates = ['u1', 'u2', 'u3', 'cx'] if backend == None else js.get('basis_gates')
    qcTrans = transpile(qc, backend=backend, layout_method=layout_method, routing_method=routing_method, scheduling_method=scheduling_method, basis_gates=basis_gates)
    return {"message": qcTrans.draw('mpl')}, 200

@app.route("/setAccount", methods=["POST"])
def setAcc():
    js = request.get_json()
    if IBMQ.active_account() == None or js.get("api_key") != IBMQ.active_account().get("token"):
        print(IBMQ.save_account(js.get("api_key"), overwrite=True))
    IBMQ.load_account()
    return {"message": "Set account successfully."}, 200

@app.route("/getAccount", methods=["GET"])
def getAcc():
    return {"message": IBMQ.active_account()}, 200

@app.route("/deleteAccount", methods=["POST"])
def delAcc():
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

@app.route("/", methods=["GET", "POST"])
def hello():
    return "Hello, World!"