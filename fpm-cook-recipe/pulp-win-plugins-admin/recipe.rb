class Pulp_win < FPM::Cookery::Recipe
  description 'Pulp Windows plugins admin extension'
  name        'pulp-win-plugins-admin'
  version     '0.1'
  revision    '1'
  homepage    'https://github.com/lsjostro/pulp_win/'
  source      'https://github.com/lsjostro/pulp_win.git', :with => :git
  arch        'noarch'
  section     'Development/Languages'

  python= [
      "python-sh",
      "msitools",
  ]

  depends python

  def build
  end

  def install
    lib('python2.6/site-packages').install_p 'pulp_win'
    lib('pulp/').install_p 'admin'
  end
end
