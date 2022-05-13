# API endpoint
## **general**
### **method:** POST
### **error:**
```
{
    error:""
}
```

## **List of APIs**
## **/qasm**
### input
- code: string of QuantumCircuit code that store in variable *qc*
```
{
    code:""
}
```
### output
- code: string of QuantumCircuit in Qasm

## **/qiskit_draw**
### input
- code: string of QuantumCircuit code that store in variable *qc*
```
{
    code:""
}
```
### output
- pic: base64 of circuit picture
```
{
    pic:""
}
```

## **/simulation**
### input
- code: string of QuantumCircuit code that store in variable *qc*
- system: name of system
- shots: number of shots to simulate
```
{
    code: "",
    system: "",
    shots: 0
}
```
### output
- result: String of object that represents the simulation result
```
{
    result: ""
}
```

## **/recommend**
### input
- api_key: key to signin to IBMQ account
- code: string of QuantumCircuit code that store in variable *qc*
```
{
    api_key: "",
    code: ""
}
```
### output
- List of configuration order by the least accumulate error
```
{
    [
        system: "",
        optlvl: 0,
        layout: "",
        routing: "",
        "acc_err": 0
    ],
    ...
}
```

## **/transpile**
### input
- api_key: key to signin to IBMQ account
- code: string of QuantumCircuit code that store in variable *qc*
- system: name of the system
- layout: type of layout method
- routing: type of routing method
- scheduling: type of scheduling method
- optlvl: number of optimization level
```
{
    api_key: "",
    code: "",
    system: "",
    layout: "",
    routing: "",
    scheduling: "",
    optlvl: 0
}
```
### output
- pic: base64 of transpile result picture
```
{
    pic: ""
}
```

## **/get_backend**
### input
- api_key: key to signin to IBMQ account
```
{
    api_key: ""
}
```
### output
- List of system that the given account can access with number of qubit and quantum volume
```
{
    [
        name: "ibmq_qasm_simulator",
        qb: 0,
        qv: 0
    ],
    ...
}
```

## **/run** (websocket)
### input
- api_key: key to signin to IBMQ account
- system: name of the system
- code: string of QuantumCircuit code that store in variable *qc*
- layout: type of layout method
- routing: type of routing method
- scheduling: type of scheduling method
- optlvl: number of optimization level
- shots: number of shots to execute

```
{
    api_key: "",
    system: "",
    code: "",
    layout: "",
    routing: "",
    scheduling: "",
    optlvl: 0,
    shots: 0
}
```
### output
- state of job
  - status: status of current job
  - queue: number of queue if in QUEUE state
  - timeToStart: estimated time to start the job
- value: result of executed circuit
```
{
    status: ""
}
```
or
```
{
    status: "QUEUE",
    queue: 0,
    timeToStart: 1:00:00.00000
}
```
or
```
{
    status: "DONE",
    value: "{0:500,1:500}"
}
```
### error
- error: if an error occur the error message will be sent
```
{
    status: "ERROR",
    error: ""
}
```