from lxml import etree
from pathlib import Path
cat=Path("Legiones Astartes.cat")
xsd=Path("Catalogue.xsd")
doc=etree.parse(str(cat))
schema_doc=etree.parse(str(xsd))
schema=etree.XMLSchema(schema_doc)
ok=schema.validate(doc)
print("VALID",ok)
for e in schema.error_log[:500]:
    print(f"{e.level_name} line={e.line} column={e.column} domain={e.domain_name} type={e.type_name}: {e.message}")
if not ok:
    raise SystemExit(1)
