import nanoid

S_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_.'
def new_sid():
    '''Generates Random ID, suited for Secret IDs'''
    return nanoid.generate(S_ALPHABET, 24)

ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz'
def new_id():
    '''Generates Random ID, suited for Internal Object IDs'''
    return nanoid.non_secure_generate(ALPHABET, 10)