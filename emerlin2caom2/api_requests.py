import requests
import pyvo as vo


def request_post(self, xml_output_name):
    """
    Post (new) target XML data onto the database.
    Note this is flipped and was formerly 'put' in torkeep.
    In recommended curl command, --data item has an @ before it. --data "@TS8004_C_001_20190801_De.xml"
    :param xml_output_name: ObservationID of xml file to post
    """
    post_file = xml_output_name
    xml_output_name = "@" + xml_output_name
    url_post = self.base_url
    headers_post = {'Content-type': 'application/xml', 'accept': 'application/xml'}
    res = requests.post(url_post, data=open(post_file, 'rb'), verify=self.rootca, headers=headers_post)
    # print(res.status_code) # can remove once code no longer needs debugging
    return res.status_code

def request_delete(self, to_del):
    """
    Deletes target XML data on the database.
    :param to_del: ObservationID of target data to delete
    """
    url_del = self.base_url + '/' + to_del
    # print(url_del) # can remove once code no longer needs debugging
    res = requests.delete(url_del, verify=self.rootca)
    if res.status_code == 204:
        print(to_del + " has been deleted.")
    else:
        print("Delete may have failed for " + to_del) # can remove once code no longer needs debugging
    return res.status_code

def request_get(self, file_to_get=''):
    """
    Get target data from database based on observations/uri. NOT YET FUNCTIONAL WITH API.
    :param file_to_get: ObservationID of file to get
    """
    payload = {'uri': file_to_get}
    #url_get = self.base_url + '/' + file_to_get
    url_get = self.base_url
    print(url_get) # can remove once code no longer needs debugging
    res = requests.get(url_get, params=payload, verify=self.rootca)
    print(res) # can remove once code no longer needs debugging


def find_existing(self, obs_id):
    """
    Use pyvo TAP service to query for existing record before
    new record is inserted, or before delete/update.
    :param obs_id: observation uri or unique identifier.
    :returns: if exists, the uuid aka primary key for db record(s) for this uri.
    """
    url_tap = self.base_url.split('/observations')[0] + '/tap'
    service = vo.dal.TAPService(url_tap)
    uuid_query = "SELECT id FROM Observation WHERE uri="+"'"+obs_id+"'"
    resultset = service.search(uuid_query)
    if len(resultset) > 1:
        print("Duplicate Records found for: " + obs_id)
        for row in resultset:
            print(row['id'])
        return resultset
        # Add Error logging here.
    elif len(resultset) == 1:
        # print(resultset[0]['id'])
        return resultset[0]['id']
    else:
        print("No existing record found for " + obs_id + ". Ok to ingest.")
        # Add Error logging here.

def request_tap(self, obs_id):
    """
    Use tap service to query for existence of observation and return uuid
    :param obs_id: observation id or meaningful uri of the observation record.
    :returns machine_id: The record id used in the database as primary key.
    """
    url_tap = self.base_url.split('/observations')[0] + '/tap/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=json&QUERY=SELECT+id+FROM+Observation+WHERE+uri=%27' + obs_id + '%27'

    if url_tap:
        print('location: ' + url_tap)
        res = requests.get(url_tap, verify=self.rootca)
        print(res)
        print(res.text)
        print(res.text[1][0])
    else:
        print("tap didn't work.")

