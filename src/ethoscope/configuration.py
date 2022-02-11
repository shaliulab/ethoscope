import yaml

CONFIG_FILE = "/etc/ethoscope.yaml"

def load_config():

    with open(CONFIG_FILE, "r") as filehandle:
        config = yaml.load(filehandle, yaml.SafeLoader)
    
    return config