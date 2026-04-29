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

## Surum

- Aktif surum: `1.1.0`
- Onceki surum `1.0.0` ile geriye donuk uyumludur. Yeni eklenen Halstead/ICC alanlari opsiyoneldir; eski payload'lar gecersiz olmaz.
- Parser ekibi `1.1.0` payload uretmeye baslar, butun ekipler entegrasyonu tamamladiginda yeni alanlar ileride zorunlu hale getirilecektir.

## Zorunlu Ust Alanlar

- `schema_version`: `1.0.0` veya `1.1.0`
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

### v1.1 ile eklenen Halstead / ICC alanlari (opsiyonel)

Asagidaki alanlar Halstead ve Improved Cyclomatic Complexity hesabini parser tarafindan saglanan sayimlarla yapmak icin eklenmistir. Boylece metrik motoru `ast.nodes[]` icinde tekrar gezerek parser isi yapmak zorunda kalmaz.

- `return_count`: fonksiyon govdesindeki `return` ifadelerinin toplam sayisi.
- `executable_lines`: yorum ve bos satirlar haric, calistirilabilir kod satiri sayisi.
- `unique_operators`: Halstead `n1`. Fonksiyonda kullanilan farkli operator turu sayisi.
- `total_operators`: Halstead `N1`. Fonksiyondaki toplam operator gecisi sayisi.
- `unique_operands`: Halstead `n2`. Fonksiyonda kullanilan farkli operand sayisi.
- `total_operands`: Halstead `N2`. Fonksiyondaki toplam operand gecisi sayisi.

Notlar:

- Bu alanlar `1.1.0` icin opsiyoneldir. Parser implementasyonu tamamlandikca payload uretirken doldurulmalidir.
- Operator/operand sayim kurallari Halstead orijinal tanimina uyacak sekilde dil bazinda parser ekibi tarafindan netlestirilir; ornek olarak Python icin tum `Operator` ve `Punctuation` token'lari operator, identifier/literal token'lari operand sayilir.
- `executable_lines` icin yorum, dokuman string'i ve bos satirlar haric tutulur.

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
