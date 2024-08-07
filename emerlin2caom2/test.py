import main_app

rootca = '/home/h14471mj/e-merlin/em_github/caom_env/caomdev/ssl/rootCA.crt'
storage_name = '/home/h14471mj/e-merlin/casa6_docker/prod/TS8004_C_001_20190801/TS8004_C_001_20190801_avg.ms'
xmldir = './data/'

main_app.emerlin_main_app(storage_name, rootca=rootca, xml_dir=xmldir)
