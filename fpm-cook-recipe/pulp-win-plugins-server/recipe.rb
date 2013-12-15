class Pulp_win < FPM::Cookery::Recipe
  description 'Pulp Windows plugins'
  name        'pulp-win-plugins-server'
  version     '0.2'
  revision    '1'
  homepage    'https://github.com/lsjostro/pulp_win/'
  source      'https://github.com/lsjostro/pulp_win.git', :with => :git
  arch        'noarch'
  section     'Development/Languages'

  #python= [
  #    "python-sh",
  #    "msitools",
  #]

  #depends python

  post_install   'postinst'

  def build
  end

  def install
    lib('pulp/plugins/').install_p 'importers'
    lib('pulp/plugins/').install_p 'distributors'
    lib('pulp/plugins/').install_p 'types' 
    etc('httpd/conf.d').install 'pulp_win.conf'
    var('www/pulp_win/http/repos').mkpath
  end
end
