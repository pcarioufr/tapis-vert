import nanoid

S_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_.'
def new_sid():
    '''Generates Random ID, suited for Secret IDs'''
    return nanoid.generate(S_ALPHABET, 24)

ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz'
def new_id():
    '''Generates Random ID, suited for Internal Object IDs'''
    return nanoid.non_secure_generate(ALPHABET, 10)


import random

colors = [
    "Almond", "Amethyst", "Apricot", "Aqua", "Azure", "Beige", "Black", "Blue", 
    "Bronze", "Brown", "Burgundy", "Byzantine", "Cerulean", "Champagne", 
    "Charcoal", "Cherry", "Cobalt", "Coral", "Crimson", "Cyan", "Emerald", 
    "Fuchsia", "Gold", "Gray", "Green", "Indigo", "Ivory", "Jade", "Lavender", 
    "Lemon", "Lilac", "Lime", "Magenta", "Maroon", "Mint", "Navy", "Olive", 
    "Orange", "Peach", "Periwinkle", "Pink", "Plum", "Purple", "Red", 
    "Rose", "Ruby", "Salmon", "Sapphire", "Silver", "Teal", "Yellow"
]

animals = [
    "Aardvark", "Albatross", "Alligator", "Antelope", "Armadillo", "Badger", 
    "Bat", "Beaver", "Bison", "Buffalo", "Camel", "Capybara", "Caribou", 
    "Chameleon", "Cheetah", "Chipmunk", "Cobra", "Cougar", "Coyote", "Crab", 
    "Crocodile", "Deer", "Dingo", "Dolphin", "Dragonfly", "Eagle", "Elephant", 
    "Elk", "Ferret", "Flamingo", "Fox", "Frog", "Gazelle", "Giraffe", "Goat", 
    "Gorilla", "Grasshopper", "Hamster", "Hedgehog", "Heron", "Hippo", 
    "Horse", "Hyena", "Iguana", "Jaguar", "Jellyfish", "Kangaroo", "Koala", 
    "Lemur", "Leopard"
]

def new_name(seed: str):

    random.seed(seed)
    return f"{random.choice(colors)} {random.choice(animals)}"
