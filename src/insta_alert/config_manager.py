import importlib
import os 
from colorama import Fore, Back

config = None

def load(config_name: str):
    """Imports and loads a config file from the 'config' directory 

    Args:
        config_name (str): The name of the config file to load
    """    
    global config
    try:
        module_path = f'insta_alert.config.{config_name}'
        config = importlib.import_module(module_path)
        print(Back.LIGHTGREEN_EX + f'Success loading config: {config_name}' + Back.RESET)
    except ImportError:
        print(Back.LIGHTRED_EX + f'Error loading config: {config_name} from directory. Error: {ImportError}' + Back.RESET)
        available_configs = get_available_configs()
        if available_configs:
            print(f'Available configs: {", ".join(available_configs)}')
        else:
            print('No available configs found. Check the config directory!')
        exit(1)
        
def get_available_configs():
    """Returns a list of available config files in the 'config' directory

    Returns:
        list: A list of available config files
    """    
    config_dir = os.path.join(os.path.dirname(__file__), 'config')
    #print(config_dir)
    if not os.path.exists(config_dir):
        print('error in getting config directory!! Are you sure directory: config exists?')
        return []
    configs = [
        f.replace('.py', '') for f in os.listdir(config_dir)
        if f.endswith('.py') and not f.startswith('__')
    ]
    return configs

if __name__ == '__main__':
    print(get_available_configs())