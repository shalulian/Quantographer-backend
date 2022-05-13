from collections import defaultdict
from io import BytesIO

import base64

import re

NAME_EXTRACTOR = re.compile(r'^([a-z]+)(.*)')

def get_available_backends(provider, addition=False):
    for backend in provider.backends():
        name = f'{backend}'

        if 'ibmq' not in name:
            continue

        config = backend.configuration()

        qb = getattr(config, 'n_qubits', None)
        qv = getattr(config, 'quantum_volume', None)

        obj = {
            'name': name,
            'qb': qb,
            'qv': qv
        }

        if addition:
            # add object to return data
            obj.update(
                {
                    'backend': backend
                }
            )

        yield obj

def get_error(gate):
    for param in gate.parameters:
        if param.name == 'gate_error':
            return param.value

    return 0

def get_errors(backend):
    # each gate can have many error
    gates_errors = defaultdict(list)

    props = backend.properties()

    # collect error of many gate
    for gate in props.gates:
        error = get_error(gate)

        match = NAME_EXTRACTOR.match(gate.name)
        name, _ = match.groups()

        gates_errors[name].append(error)

    # normalize errors
    for gate, errors in gates_errors.items():
        gates_errors[gate] = sum(errors) / len(errors)

    return dict(gates_errors)

def calc_error(ops_dict, error_dict):
    # initial value
    p_not_errors = 1.0

    for gate_name, amount in ops_dict.items():
        try:
            p_err = error_dict[gate_name]
        except:
            # skip gate with unknown error
            pass
        else:
            # accumulate error
            p_not_errors *= (1.0 - p_err) ** amount

    return (1.0 - p_not_errors) * 10000 # move decimal point

def plot_png(fig):
    # create memory stream
    mem_file = BytesIO()

    # export fig as PNG iamge
    fig.savefig(mem_file, format='png', bbox_inches='tight')

    return mem_file.getvalue()

def to_data_url(mime, val):
    # convert to base64
    buffer = base64.b64encode(val).decode('ascii')

    return f'data:{mime};base64,{buffer}'
