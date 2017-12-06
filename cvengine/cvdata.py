import ssl
import urllib2
import yaml


class CVData():
    """Class to encapsulate all configuration information for running scenario

    This class is used to store all configuration data for the running
    container validation scenario, including the container image, the
    metadata file information, the target environment and platform, and
    any artifacts to retrieve.

    Attributes:
        image_url (str): The location of the container image
        metadata (dict): The data in yaml format as pulled from the metadata
            file
        scenario (dict): The data for the target platform pulled from the
            metadata
        artifacts (list): A list of artifacts to be retrieved from the
            container and test host
        environment (dict): A dictionary of configuration information for
            the target environment
    """
    def __init__(self, image_url, cvdata_url, config):
        self.image_url = image_url
        self.metadata = self.fetch_metadata(cvdata_url)
        self.scenario = self.parse_scenario(self.metadata, config)
        self.artifacts = self.metadata['Artifacts']
        self.environment = config.get('environment')

    def fetch_metadata(self, url):
        """Downloads the metadata file and parses its contents

        Helper function to fetch the metadata file and parse the yaml contents
        into a dictionary.

        Args:
            url (str): The URL to the metadata file

        Returns:
            dict: The contents of the metadata file
        """
        print('Downloading metadata file from {0}'.format(url))
        context = ssl._create_unverified_context()
        raw_data = urllib2.urlopen(url, context=context).read()
        metadata = yaml.load(raw_data)

        print 'The metadata contents are: {0}'.format(metadata)
        return metadata

    def parse_scenario(self, metadata, config):
        """Determines the target scenario from the metadata file

        Fetches the target container platform from the scenario config
        then parses the corresponding config for the target platform
        from the metadata information. If no target platform is specified,
        a default target platform will be used.

        Args:
            metadata (dict): The scenario metadata information
            config (dict): The scenario config

        Returns:
            dict: The metadata information for the target scenario
        """
        target_platform = config.get('target_host_platform', None)
        scenario = None
        for platform in metadata['Test']:
            if ((platform['host_type'] == target_platform) or
                    (platform.get('default', False) and target_platform
                     is None)):
                scenario = platform
                break

        return scenario
