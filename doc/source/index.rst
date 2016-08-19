.. MASS Client documentation master file, created by
   sphinx-quickstart on Thu Aug 11 09:31:42 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the MASS Client Documentation
========================================

The MASS Client package consists of base classes to connect your own
malware analysis tool to MASS. This frees your analysis tool from dealing with
the details of MASS' REST API and keeps an analysis client in as simple as possible.

Here is an example of how an analysis client could look like:
    
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

For more details and how to run the client have a look at the :doc:`tutorial`.


Contents:

.. toctree::
   :maxdepth: 2

   tutorial
   api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

