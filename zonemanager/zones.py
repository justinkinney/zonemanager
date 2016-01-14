import route53
import logging
import os
import yaml
import dns.zone
import sys
from zonemanager.utils import load_yaml

log = logging.getLogger()

RDTYPE_SYNC_FILTER = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'PTR']  # only sync these record types


class RecordSet(object):

    def __init__(self, name, rtype, ttl, values):
        self.name = name
        self.rtype = rtype
        self.ttl = ttl
        self.values = set(values)

    def __eq__(self, other):
        """ Compare a resource record by name """
        return (
            (self.name, self.rtype, self.ttl, self.values) ==
            (other.name, other.rtype, other.ttl, other.values)
        )

    def __repr__(self):
        return 'RecordSet<{}> <{}, {}, {}>'.format(
            self.name, self.rtype, self.ttl,
            self.values
        )


class Zone(object):
    def __init__(self, zone):
        """ Initialize a zonemanager.Zone from a dns.zone.Zone"""
        self.zone = zone
        self.domain = self.zone.origin.to_text().strip('.')

    @classmethod
    def from_yaml_file(cls, filename):
        """ Return a dns.zone.Zone object loaded from a given yaml file """
        zone_content = load_yaml(filename)
        origin = zone_content['origin']
        soa_found = False

        lines = []
        for rec in zone_content['data']:

            rname = rec['name']
            rtype = rec['type']
            ttl = rec['ttl']
            values = rec['values']

            # detect and alert on presence of more than one SOA record
            if rtype == 'SOA' and soa_found:
                raise RuntimeError('Found more than one SOA record')

            # detect multiple values in the SOA record
            if rtype == 'SOA' and rname == origin:
                if len(values) > 1:
                    raise RuntimeError('Found more than one value for SOA record')
                lines.append(cls._format_record('@', ttl, rtype, values[0]))
                soa_found = True
                continue

            # create a line for each value defined for the record
            # verify that CNAME, MX, NS records have a fqdn defined in values
            for value in values:
                if rtype in ['CNAME', 'MX', 'NS'] and '.' not in value:
                    raise RuntimeError(
                        'Could not find FQDN in target of CNAME record: {}'.format(rname)
                    )
                lines.append(cls._format_record(rname, ttl, rtype, value))

        # pass the assembled contents to dns.zone.from_text()
        zone_string = '\n'.join(lines) + '\n'
        zone = dns.zone.from_text(zone_string, origin=origin)
        zone_obj = cls(zone)
        return zone_obj

    @staticmethod
    def _format_record(rname, ttl, rtype, value):
        return '{} {} IN {} {}'.format(rname, ttl, rtype, value)

    def _extract_values(self, rset):
        """ Return the usable components of the rset value"""
        return [' '.join(r.split(' ')[3:]) for r in rset.to_text().splitlines()]

    def _as_dict(self):
        """ Render a dns.zone.Zone as a dictionary """
        zone = {}
        zone['origin'] = self.zone.origin.to_text()
        origin = zone['origin']
        rset_list = []
        for rset in self.zone.iterate_rdatasets():
            values = self._extract_values(rset[1])
            rtype = dns.rdatatype.to_text(rset[1].rdtype)

            # convert '@' to origin name
            name = origin if (rset[0].to_text() == '@') else rset[0].to_text()

            # ensure CNAME, MX, NS record targets include fqdn by appending
            # the zone origin to them
            if rtype in ['CNAME', 'MX', 'NS']:
                values = [
                    '{}.{}'.format(v, origin)
                    for v in values if '.' not in v
                ]

            # expand in-zone records to fqdn
            if not name.endswith(origin):
                name += '.' + origin

            rset_list.append(
                {
                    'name': name,
                    'type': rtype,
                    'ttl': int(rset[1].ttl),
                    'values': values
                }
            )

        zone['data'] = rset_list
        return zone

    def yaml(self):
        """ Return a dns.zone.Zone rendered as yaml """
        return yaml.dump(self._as_dict(), default_flow_style=False)

    def write(self, dest):
        """ Write the zone contents as yaml """
        if dest == 'stdout' and sys.stdout.isatty():
            print self.yaml()
        else:
            with open(dest, 'w') as f:
                f.write(self.yaml())

    def records(self, rdtypes=RDTYPE_SYNC_FILTER):
        """
        Return a list of RecordSets that match the type in rdtypes
        Note: the datasource here is the dns.zone.Zone object, so we have
        to do some munging of the records.
        """
        records = []
        origin = self.zone.origin.to_text()
        for rec in self.zone.iterate_rdatasets():
            rtype = dns.rdatatype.to_text(rec[1].rdtype)
            ttl = rec[1].ttl
            fqdn = rec[0].to_text()
            if rtype in rdtypes:
                values = [i.to_text() for i in rec[1].items]

                # replace '@' with the zone origin
                fqdn = fqdn.replace('@', origin)

                # expand in-zone records to fqdn
                if not fqdn.endswith(origin):
                    fqdn += '.' + origin

                # ensure CNAME, MX, NS record targets include fqdn by appending
                # the zone origin to them
                if rtype in ['CNAME', 'MX', 'NS']:
                    values = [
                        '{}.{}'.format(v, origin)
                        for v in values if '.' not in v
                    ]

                records.append(RecordSet(fqdn, rtype, ttl, values))

        return records


class Route53Zone(object):

    def __init__(self, zone):
        access_id = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.client = route53.connect(access_id, secret_key)
        self.zone = None
        self.set_zone(zone)

    def set_zone(self, zone):
        log.debug('Setting route53 zone to {}'.format(zone))
        try:
            for z in self.client.list_hosted_zones():
                log.debug('name: {} id: {}'.format(z.name, z.id))
                if z.name == '{}.'.format(zone):
                    self.zone = self.client.get_hosted_zone_by_id(z.id)
        except Exception:
            log.exception("Couldn't load zone: {}".format(zone))
            raise

        if self.zone is None:
            raise RuntimeError('Failed to load zone: {}'.format(zone))

    def records(self, rdtypes=RDTYPE_SYNC_FILTER):
        """ Return a list of RecordSets that match the type in rdtypes """
        if not self.zone:
            return None

        records = []
        for rec in self.zone.record_sets:
            if rec.rrset_type in rdtypes:
                records.append(
                    RecordSet(
                        rec.name,
                        rec.rrset_type,
                        rec.ttl,
                        rec.records
                    )
                )

        return records

    def create_record(self, recordset):
        """ Create a record in this zone in Route 53 """
        log.debug('Creating record in r53 for {}'.format(recordset))
        create_func = getattr(
            self.zone, 'create_{}_record'.format(recordset.rtype.lower())
        )
        log.debug('Using create function: {}'.format(create_func))
        result = create_func(
            name=recordset.name,
            values=list(recordset.values),
            ttl=recordset.ttl
        )
        log.debug('result from route53: {}'.format(result))


class ZoneSyncManager(object):

    def __init__(self, local_zone,  r53_zone, dryrun=False):
        log.debug('Initializing ZoneSyncManager')
        self.dryrun = dryrun
        self.r53_zone = r53_zone
        self.r53_records = list(r53_zone.records())
        self.local_records = list(local_zone.records())
        self.updates = []
        self.creates = []
        self.orphans = []

    def run(self):
        """ Synchronize a local dns.zone.Zone with Route53 """

        # first collect strictly non-matching records
        nonexistent = [rec for rec in self.local_records if rec not in self.r53_records]

        # since some records may exist, but don't strictly match (i.e. updated values),
        # filter and perform updates for these
        updates = [rec for rec in nonexistent if rec.name in [r.name for r in self.r53_records]]
        for rec in updates:
            nonexistent.remove(rec)
            for r in self.r53_zone.zone.record_sets:
                if r.name == rec.name and r.rrset_type == rec.rtype:
                    r.records = list(rec.values)
                    if not self.dryrun:
                        r.save()
                    self.updates.append((rec.name, rec.rtype))

        # finally, create the records that are truly non-existent
        for rec in nonexistent:
            if not self.dryrun:
                self.r53_zone.create_record(rec)
            self.creates.append((rec.name, rec.rtype))

        self.orphans = [rec.name for rec in self.r53_records if rec not in self.local_records]

    def report(self):
        """log a report of actions in the zone"""
        if self.dryrun:
            pre = '[dryrun] Would have '
        else:
            pre = ''

        log.info('{}Created {} new records: {}'.format(pre, len(self.creates), self.creates))
        log.info('{}Updated {} existing records: {}'.format(pre, len(self.updates), self.updates))
        log.info('{}Detected {} orphaned records: {}'.format(pre, len(self.orphans), self.orphans))
