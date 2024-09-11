import main_app

rootca = '/Users/user/repos/emerlin2caom/scripts/rootCA.pem'
storage_name = '/Users/user/dataReduction/TS8004_C_001_20190801/TS8004_C_001_20190801_avg.ms'
xmldir = '/Users/user/repos/emerlin2caom/output_xml/'

main_app.emerlin_main_app(storage_name, rootca=rootca, xml_dir=xmldir)
