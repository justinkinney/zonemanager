"""This module implements a CLI using the click library [http://click.pocoo.org/]"""
import click
import dns.zone
import logging
import sys

from zonemanager.zones import Zone, Route53Zone, ZoneSyncManager
from zonemanager.utils import set_env_aws_creds

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


@click.group()
@click.version_option()
@click.option('--debug', default=False, is_flag=True, help='enable debugging output')
@click.option('--quiet', default=False, is_flag=True, help='disable all output to stdout')
@click.option('--logfile', type=click.Path(), default=None,
              help='log to the specified logfile in addition to stdout')
def cli(debug, logfile, quiet):
    """Route53 Manager.

    This tool assists in managing Route53 zones. There are 2 basic modes of operations:\n
     * import - imports zone content from a file, a zone XFER, or Route53. Output is
     written to to stdout or a YAML file if filename is specified.\n
     * apply - applies the content of a specified YAML file to a Route53 zone.
    """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # quiet overrides other options
    if quiet:
        debug = False
    if logfile:
        log.info('logging to {}'.format(click.format_filename(logfile)))
        fh = logging.FileHandler(logfile)
        fh.setFormatter(formatter)
        log.addHandler(fh)
    if sys.stdout.isatty() and not quiet:
        log.info('Detected console - copying logs to stdout')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log.addHandler(ch)
    if debug:
        log.setLevel(logging.DEBUG)
        log.debug('Debug mode: on')


@cli.group('import')
def import_zone():
    """import zone contents.

    In import mode, there are two arguments: SOURCE and DEST. SOURCE can be one of
    'file' or 'xfer'. DEST should be the YAML filename to write the zone content to.
    """


@import_zone.command('file')
@click.argument('source', type=click.Path(exists=True))
@click.argument('dest', type=click.Path(exists=False), default='stdout')
def file_import(source, dest):
    """import a zone from a BIND zone file"""
    log.info("importing from: {} writing to: {}".format(source, dest))

    try:
        zone = Zone(dns.zone.from_file(source))
    except Exception as e:
        log.exception('Exception while processing {}: {}'.format(source, e))
        raise

    try:
        zone.write(dest)
    except Exception as e:
        log.exception('Exception while processing {}: {}'.format(source, e))
        raise

    log.info("Wrote zone to {}".format(dest))


@import_zone.command('xfer')
@click.argument('source', default=None)
@click.argument('zone', default=None)
@click.argument('dest', type=click.Path(exists=False), default=None)
def xfer_import(source, zone, dest):
    """import a zone from a BIND zone XFER"""
    log.info("importing {} from: {} writing to: {}".format(zone, source, dest))
    try:
        zone = Zone(dns.zone.from_xfr(source))
    except Exception as e:
        log.exception('Exception while processing {}: {}'.format(source, e))
        raise

    try:
        zone.write(dest)
    except Exception as e:
        log.exception('Exception while processing {}: {}'.format(source, e))
        raise

    log.info("Wrote zone to {}".format(dest))


@cli.command('apply')
@click.argument('source', type=click.Path(exists=True), default=None)
@click.argument('zone', default=None)
@click.option('--dryrun', default=False, is_flag=True, help='enable dryrun mode')
@click.confirmation_option(prompt='Are you sure you want to sync to route53?')
def apply(source, zone, dryrun):
    """apply zone updates.

    In apply mode, there are two arguements: SOURCE and ZONE. SOURCE should be a filename,
    and DEST should be the zone name to apply to.
    """
    log.info('reading zone content from {}'.format(source))
    zone_from_file = Zone.from_yaml_file(source)

    log.info('reading zone content from route53')
    set_env_aws_creds()
    r53_zone = Route53Zone(zone)

    zone_syncer = ZoneSyncManager(zone_from_file, r53_zone, dryrun)
    zone_syncer.run()
    zone_syncer.report()


cli.add_command(import_zone)
cli.add_command(apply)
