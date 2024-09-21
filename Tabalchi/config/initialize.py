#(C) Shreyan Mitra

class Initializer():
    def __init__(self):
        with open(".init", "r") as file:
            for line in file.readlines():
                components = line.split("=")
                var_name = (components[0]).replace(" ", "")
                value = (components[1]).strip()
                setattr(self, var_name, value)
