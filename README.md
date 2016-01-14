# zone manager for route53

This tool is intended to simplify management of a route53 zone by holding the entire zone configuration in a yaml file. When run, the existing zone is interrogated and compared to the configuration. Differences are then applied to the zone.

In addition to managing the zone from a yaml file, this tool supports importing from a BIND zone file or a zone XFER.

There are three basic modes of operation:

* import mode - where you can import configuration from another format (bind format or zone XFER)
* apply mode - where you can actually apply changes

## INSTALLATION

Clone the repo:
```
git clone https://github.com/justinkinney/zonemanager.git
```

Make a virtualenv and install requirements:
```
cd zonemanager
virtualenv <dir>
source <dir>/bin/activate
pip install -r requirements.txt
python setup.py install
```

Use the tool:
```
manage
```

## CONFIGURATION
Zonemanager uses your `~/.aws/credentials` file to automatically populate credentials.

Create the file if it doesn't exist, using the following template as an example:
```
[default]
aws_access_key_id = AKIA...Q
aws_secret_access_key = 2b...cV
```

## USAGE
```
Usage: manage [OPTIONS] COMMAND [ARGS]...

  Route53 Manager.

  This tool assists in managing Route53 zones. There are 2 basic modes of
  operations:

   * import - imports zone content from a file, a zone XFER, or Route53.
   Output is  written to a YAML file.

   * apply - applies the content of a specified YAML file to a Route53 zone.

Options:
  --version       Show the version and exit.
  --debug         enable debugging output
  --logfile PATH  log to the specified logfile in addition to stdout
  --help          Show this message and exit.

Commands:
  apply   apply zone updates.
  import  import zone contents.
```

## EXAMPLES

### Import Options
```
Usage: manage import [OPTIONS] COMMAND [ARGS]...

  import zone contents.

  In import mode, there are two arguments: SOURCE and DEST. SOURCE can be
  one of 'file', 'xfer', or 'route53'. DEST should be the YAML filename to
  write the zone content to.

Options:
  --help  Show this message and exit.

Commands:
  file  import a zone from a BIND zone file
  xfer  import a zone from a BIND zone XFER
```

* Importing a zone from a Bind configuration file:
```
manage import file <zone_filename> <output_filename>
```

* Importing a zone from a zone XFER:
```
manage import xfer <dns_server_IP> <zone> <output_filname>
```

### Sync Options
```
Usage: manage apply [OPTIONS] SOURCE ZONE

  apply zone updates.

  In apply mode, there are two arguements: SOURCE and ZONE. SOURCE should be
  a filename, and DEST should be the zone name to apply to.

Options:
  --dryrun  enable dryrun mode
  --yes     Confirm the action without prompting.
  --help    Show this message and exit.
```

* Syncing a zone to Route53:
```
$ manage apply conf/example.com.yml example.com
Are you sure you want to sync to route53? [y/N]: y
2016-01-14 12:37:51,516 - root - INFO - reading zone content from conf/example.com.yml
2016-01-14 12:37:51,535 - root - INFO - reading zone content from route53
2016-01-14 12:37:51,536 - root - INFO - Sourcing AWS credentials [default] from ~/.aws/credentials
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba47ea8>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba47d88>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba59638>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba47ea8>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba59710>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba47d88>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba47ea8>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba59c20>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10ba59c20>
2016-01-14 12:37:53,372 - root - INFO - Created 0 new records: []
2016-01-14 12:37:53,372 - root - INFO - Updated 0 existing records: []
2016-01-14 12:37:53,372 - root - INFO - Detected 1 orphaned records: ['x.example.com.']
```

* Enable debug output while syncing:
```
$ manage --debug apply conf/example.com.yml example.com
```

* Enable debug output and logfile capture while syncing:
```
$ manage --logfile logfile.log --debug apply conf/example.com.yml example.com
```

* Dryrun to test change:
```
$ manage apply --dryrun conf/example.com.yml example.com
Are you sure you want to sync to route53? [y/N]: y
2016-01-14 12:40:13,448 - root - INFO - reading zone content from conf/example.com.yml
2016-01-14 12:40:13,463 - root - INFO - reading zone content from route53
2016-01-14 12:40:13,463 - root - INFO - Sourcing AWS credentials [default] from ~/.aws/credentials
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5c1ea8>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5c1d88>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5d3638>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5c1ea8>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5d3710>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5c1d88>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5c1ea8>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5d3c20>
<Element {https://route53.amazonaws.com/doc/2012-02-29/}HostedZone at 0x10f5d3c20>
2016-01-14 12:40:15,158 - root - INFO - [dryrun] Would have Created 0 new records: []
2016-01-14 12:40:15,158 - root - INFO - [dryrun] Would have Updated 0 existing records: []
2016-01-14 12:40:15,158 - root - INFO - [dryrun] Would have Detected 1 orphaned records: ['x.example.com.']
```

* Fully automatic mode for use with integration tools:
```
$ manage --quiet --logfile logfile.txt apply --yes conf/example.com.yml example.com
```


