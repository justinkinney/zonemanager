import ConfigParser
import logging
import os
import sys
import yaml

log = logging.getLogger()


def load_yaml(filename):
    with open(filename, 'r') as stream:
        return yaml.load(stream)


def set_env_aws_creds(account='default'):
    """
    Parse ~/.aws/credentials for credentials
    Allow OS environment variables to override (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
    Exit script of neither can be found
    """

    # grab creds from env
    aws_key_env_var = "AWS_ACCESS_KEY_ID"
    aws_secret_env_var = "AWS_SECRET_ACCESS_KEY"
    aws_key_val = os.getenv(aws_key_env_var)
    aws_secret_val = os.getenv(aws_secret_env_var)

    # if no env variables are set, source them from the config file
    if not aws_key_val or not aws_secret_val:
        creds_file_path = os.path.expanduser("~/.aws/credentials")
        if os.path.exists(creds_file_path):
            cfg_parser = ConfigParser.ConfigParser()
            cfg_parser.read(creds_file_path)
            if account in cfg_parser.sections():
                try:
                    tmp_aws_key_val = cfg_parser.get(account, aws_key_env_var.lower())
                    tmp_aws_secret_val = cfg_parser.get(account, aws_secret_env_var.lower())
                except ConfigParser.NoOptionError:
                    log.fatal("AWS credentials file misconfigured")
                    sys.exit(1)
                else:
                    log.info("Sourcing AWS credentials [{}] from ~/.aws/credentials".format(account))
                    os.environ[aws_key_env_var] = tmp_aws_key_val
                    os.environ[aws_secret_env_var] = tmp_aws_secret_val

    # validate that values are exported into environment
    aws_key_val = os.getenv(aws_key_env_var)
    aws_secret_val = os.getenv(aws_secret_env_var)

    if not aws_key_val:
        log.fatal("Environment variable: AWS_ACCESS_KEY_ID not set.")
    if not aws_secret_val:
        log.fatal("Environment variable: AWS_SECRET_ACCESS_KEY not set.")
    if not aws_key_val or not aws_secret_val:
        sys.exit(1)
