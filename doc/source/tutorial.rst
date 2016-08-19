MASS Client Tutorial
=====================

In this tutorial we are going to create an analysis client which analyses the
size of the file of a malware sample. While this is not increadibly usefull it
will show all steps which are needed to connect your own analysis to a MASS
server. 

There are basicly three steps we need to make:

  - Inherit from the right base class
  - Download the file and analyze it
  - Send the result back to MASS

Creating an Analysis Client
---------------------------

Creating a new MASS client is based on inheriting from a class which already
handles all implementation details and lets you focus on the actual analysis of
the sample. There are four base classes for analysis systems
:class:`mass_client.FileAnalysisClient`,
:class:`mass_client.DomainAnalysisClient`, :class:`mass_client.IPAnalysisClient`
and :class:`mass_client.URIAnalysisClient` to analyse Files, Domains, IP
Adresses and URIs respectively.

In this tutorial we are going to build a analysis client for files, hence we are
going to inherit our class from :class:`mass_client.FileAnalysisClient`.

.. code-block:: python

    from mass_client import FileAnalysisClient

    class SizeAnalysisInstance(FileAnalysisClient):
        def __init__(self, config):
            super(SizeAnalysisInstance, self).__init__(config)

        def do_analysis(self, analysis_request):
            # DO FILE ANALYSIS HERE


The :class:`mass_client.FileAnalysisClient` class will already do consistency
checks, e.g. if the analysis request which the client recieved is actually a
file etc. It will also setup an object variable :any:`self.sample_dict`. This
dictionary contains all meta-information of the sample.

.. TODO beispiel für self.sample_dict einfügen

Since we want to analyse the size of the file we want to download the file from
mass. For convinience the :class:`mass_client.FileAnalysisClient` class has an
context manager :func:`mass_client.FileAnalysisClient.temporary_sample_file` to
download the file to a temporary location. The yielded variable will be a string
with the file path, _not_ a fileobject. Using the filename we can easily find
out the size of the file

.. code-block:: python

    with self.temporary_sample_file() as filename:
        file_size = os.path.getsize(filename)

Now that we have the size of the file, we want to send our result back to the
MASS server. For this purpose the analysis client has the
:any:`FileAnalysisClient.send_report` method.

We can hand over our results to the MASS server in three ways. 


#.  We can decide that our results are additional meta data :

    .. code-block:: python

        self.submit_report(analysis_request['url'],
                           additional_metadata={'file size': file_size}
                           )


#. We can send an python dictionary (encoded in json) which contains our results:

    .. FIXME warum hat das hier eine andere einrückungstiefe?!

    .. code-block:: python

        report = {'file size': file_size}
        self.submit_report(analysis_request['url'],
                       json_report_objects={'file size analysis': report}
                       )


#. We could send a raw data file which contains our analysis:

    .. code-block:: python

        file_size_blob = str(file_size).encode('ascii')
        self.submit_report(analysis_request['url'],
                            raw_report_objects={'file size analysis': file_size_blob}
                           )

Of course we can do any combination of these three. Please note that additional
meta data is going to be safed in the report json object on the MASS server
directly. For json and raw report objects the report json object will contain an
link to the actual object.

.. TODO hier ein Beispiel angeben.

This means that for the sake of performance any larger analysis report should be
either send as json report object or raw report object. Otherwise when
retrieving a list of all reports at http://your-mass-server/api/report/ all
report information will be loaded too which can get arbitrarily slow.

For our case it is quite reasonable to submit the file size as additional meta
data. Hence our complete example would look like this:

.. code-block:: python

    from mass_client import FileAnalysisClient
    from mass_client import temporary_sample_file
    import os

    class SizeAnalysisInstance(FileAnalysisClient):
        def __init__(self, config):
            super(SizeAnalysisInstance, self).__init__(config)

        def do_analysis(self, analysis_request):
            """ Analyse the size of the file.
            """
            with self.temporary_sample_file() as file:
                file_size = os.path.getsize(file)
                file_size_report = {'file size': file_size}
                self.submit_report(analysis_request['url'], 
                                   additional_metadata=file_size_report
                                   )


Configure an Analysis Client
-----------------------------

The config is a :any:`configparser.ConfigParser()` object usually read from a
INI file. A minimal example of a configuration could be:

.. code-block:: ini

    [GLOBAL]
    ServerURL = http://localhost:5000/
    APIEndpoint = api/
    SleepTime = 3

    [SizeAnalysisInstance]
    PollTime = 10
    UUID = f27f964c-2cc7-4eb9-a0a1-6bfbb32e4d51
    SystemName = size_analysis
    mass api key = foo_key


The mandatory fields for the global section are

* *ServerURL*: This is the URL of the server MASS is running on.
* *APIEndpoint*: The relative URL for the REST API.
* *SleepTime*: The time duration to wait between two request cycles.

The mandatory fields for a analysis client section are

* *PollTime*: time duration to wait before the clients polls the server if any new
  requests are present
* *UUID*: a unique identifier, this can be either generated on the MASS web user--
  interface or for example by uuidgen.
* *SystemName*: unique name of this analysis client, the name has to be unique on
  the individual MASS server only
* *mass api key*: On each request the client has to authenticate itself, this is
  done by a client specific API key. The API key can only be generated by an
  admin of the MASS server installation you want to connect your client to.
  If you are the admin the relative URL where you can generate API keys is
  ``webui/admin/analysis_systems/``.

Of course you can add more fields to your client section.

Running an Analysis Client
---------------------------

The analysis client base class is inherited from :class:`threading.Thread`,
hence we can run our client as a separate thread easily.

.. code-block:: python

    client = SizeAnalysisInstance(config)
    client.start()


Creating Relations between Samples
----------------------------------

Your analysis client maybe finds other file, IP, URL or domain samples during
its analysis. Those can be submitted as new samples to MASS. Additionally you
can tell MASS that the newly found sample is related to the sample the analysis
client is currently analysing. You can do this by submitting a sample relation.

The currently available relations are:

* dropped-by : relation between a file and a sample, the file was somehow
  dropped, e.g. extracted, from the sample
* resolved-by: relation between a domain and a sample, i.e. the domain was resolved by the sample.
* contacted-by: relation between an IP address and a sample, the IP was contacted
  by the sample, for example during a dynamic analysis 
* retrieved-by: relation between an HTTP(S) URL  and a sample, i.e. the URL was retrieved by the sample.
