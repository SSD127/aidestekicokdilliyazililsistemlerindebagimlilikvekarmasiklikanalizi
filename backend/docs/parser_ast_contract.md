# PolyMetric Parser AST Sozlesmesi

Bu belge parser ekibinin backend'e teslim edecegi AST JSON yapisinin resmi v1 sozlesmesidir.

## Referans Dosyalar

- JSON schema: `backend/contracts/parser_ast.schema.json`
- Ornek payload: `backend/contracts/examples/golden_parser_ast.json`

## Amac

Parser ekibi Tree-sitter ciktisini dogrudan backend'in tuketebilecegi ortak bir ara formata donusturur.
Bu format:

- dil bagimsizdir,
- AST detayini kaybetmez,
- fonksiyon / class / import / branch / loop gibi ust seviye alanlari acikca tasir,
- sonraki adimda metrik motorunun `analysis_result` payload'ina donusmesini kolaylastirir.

## Zorunlu Ust Alanlar

- `schema_version`: su an sabit `1.0.0`
- `parser_version`: parser implementasyon surumu
- `repository`: repo URL, ref, commit hash ve analiz zamani
- `files[]`: parse edilen dosyalar

## Her Dosyada Zorunlu Alanlar

- `file_path`
- `language`
- `summary`
- `imports[]`
- `functions[]`
- `classes[]`
- `ast`

## `summary` Alani

Backend ve metrik motoru icin dosya seviyesinde hizli ozet verir:

- `loc_total`
- `loc_code`
- `function_count`
- `class_count`
- `branch_count`
- `loop_count`
- `import_count`

## `functions[]` Alani

Metrik motorunun dogrudan kullanacagi yapi:

- `name`
- `qualified_name`
- `kind`
- `parameters[]`
- `branch_count`
- `loop_count`
- `location`
- `ast_node_id`

## `ast.nodes[]` Alani

Tam AST/CST bilgisinin hafifletilmis ama kayipsiz temsilidir.
Her dugum:

- `id`
- `type`
- `parent_id`
- `field_name`
- `named`
- `text`
- `location`

alanlarini tasiyabilir.

## Kural

Parser ekibi backend'e verecegi veriyi bu schema ile uyumlu uretecek.
Alan adi degisikligi, tip degisikligi veya yeni zorunlu alan ekleme ihtiyaci olursa once backend ile sozlesme guncellenecek.
