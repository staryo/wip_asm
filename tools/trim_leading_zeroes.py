def trim_zeroes(identity):
    if identity[:6] == '000000':
        return identity[6:]
    return identity