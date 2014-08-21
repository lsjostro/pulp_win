pulp_win
========

Initial Pulp plugin to handle Windows MSI packages

WARNING: Might be lots of bugs. 

### Requirements

Need the following to be able to upload MSIs from Linux:
  *  python-sh
  *  msitools-0.01 

http://bonzini.fedorapeople.org/msitools-0.01.tar.gz

### Installation

Build the RPMs from spec file

```
Example Usage:

    ~ $  pulp-admin win repo create --serve-http=true  --repo-id win-test-repo
    Successfully created repository [win-test-repo]
    
    ~ $  pulp-admin win repo uploads msi -f nxlog-ce-2.5.1089.msi --repo-id win-test-repo
    +----------------------------------------------------------------------+
                                  Unit Upload
    +----------------------------------------------------------------------+
    
    Extracting necessary metadata for each request...
    [==================================================] 100%
    Analyzing: nxlog-ce-2.5.1089.msi
    ... completed
    
    Creating upload requests on the server...
    [==================================================] 100%
    Initializing: nxlog-ce-2.5.1089.msi
    ... completed
    
    Starting upload of selected units. If this process is stopped through ctrl+c,
    the uploads will be paused and may be resumed later using the resume command or
    cancelled entirely using the cancel command.
    
    Uploading: nxlog-ce-2.5.1089.msi
    [==================================================] 100%
    3584000/3584000 bytes
    ... completed
    
    Importing into the repository...
    ... completed
    
    Deleting the upload request...
    ... completed
    
    ~ $  pulp-admin win repo publish run --repo-id win-test-repo 
    +----------------------------------------------------------------------+
                     Publishing Repository [win-test-repo]
    +----------------------------------------------------------------------+
    
    This command may be exited by pressing ctrl+c without affecting the actual
    operation on the server.
    
    Publishing packages...
    [==================================================] 100%
    Packages: 1/1 items
    ... completed
    
    Publishing repository over HTTP
    [-]
    ... completed

    ~ $  pulp-admin win repo content msi  --repo-id win-test-repo
    Checksum:     06f3a9975ae920aa6058887cc5be55c5
    Checksumtype: md5
    Filename:     nxlog-ce-2.5.1089.msi
    Name:         NXLOG-CE
    Version:      2.5.1089

```

