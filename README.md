pulp_win
========

Initial Pulp plugin to handle Windows MSI packages

WARNING: Might be lots of bugs. 

### Requirements

Need the following to be able to upload MSIs from Linux
    python-sh
    msitools-0.01 

http://bonzini.fedorapeople.org/msitools-0.01.tar.gz

### Installation

Build the RPMs with fpm-cookery

```
Server:
    $ gem install fpm-cookery
    $ cd fpm-cook-recipe/pulp-win-plugins-server
    $ fpm-cook
    $ sudo rpm -Uvh pkg/*.rpm

Admin extension:
    $ cd fpm-cook-recipe/pulp-win-plugins-admin
    $ fpm-cook
    $ sudo rpm -Uvh pkg/*.rpm
```
