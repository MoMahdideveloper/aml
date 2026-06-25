# Maskan Property Field Audit (20 Listings)

- Source: `maskan-file.ir` detail pages
- Authentication: loaded from `cookiesmaskan.txt`
- Audited listings: 20

## Detected Fields and Mapping

| Maskan Label | Seen In | Sample Values | Mapped Property Field |
|---|---:|---|---|
| سند | 20 | وکالتی, شش دانگ ملکی, قولنامه ای | `custom_fields` |
| قابلیت معاوضه | 20 | دارد, ندارد | `custom_fields` |
| تعداد خواب | 19 | 1, 2, 0 | `custom_fields` |
| تعداد طبقات | 19 | 5, 6, 3 | `custom_fields` |
| تعداد واحدها | 19 | 10, 30, 4 | `custom_fields` |
| دیوارپوش | 19 | کاغذ دیواری, نقاشی, گچ | `custom_fields` |
| زیربنا | 19 | 75, 103, 120 | `custom_fields` |
| سرمایش | 19 | کولرآبی, کولر گازی, ندارد | `custom_fields` |
| سن بنا | 19 | 9 سال ساخت, 3 سال ساخت, 2 سال ساخت | `custom_fields` |
| طبقه | 19 | 1, 3, 4 | `custom_fields` |
| قیمت هر متر زیربنا | 19 | 46,666,667 تومان, 75,728,155 تومان, 37,500,000 تومان | `custom_fields` |
| گرمایش | 19 | پکیج, بخاری, شومینه | `custom_fields` |
| کابینت | 18 | ام دی اف, فلز, های گلس | `custom_fields` |
| کفپوش | 18 | سرامیک, موکت, موزاییک | `custom_fields` |
| جهت ملک | 17 | جنوبی, دونبش, شمالی | `custom_fields` |
| نما | 15 | سنگ, آجر | `custom_fields` |
| حاشیه ملک | 5 | 4.5 متر, 4 متر, 8 متر | `custom_fields` |
| قیمت هر متر | 5 | 54,320,988 تومان, 46,913,580 تومان, 100,000,000 تومان | `custom_fields` |
| ارتفاع | 1 | 4.00 | `custom_fields` |
| تجاری | 1 | دائم | `custom_fields` |
| تراکم | 1 | زیاد(4طبقه به بالا) | `custom_fields` |
| تعداد سقف | 1 | 0 | `custom_fields` |
| سقف پروانه | 1 | نامشخص | `custom_fields` |
| طول | 1 | 0 | `custom_fields` |
| کاربری | 1 | مسکونی | `custom_fields` |

## Notes

- Common apartment/villa fields are now represented as first-class `Property` columns.
- Rare/special cases can be preserved in `custom_fields` as raw JSON/text.
- Pricing conventions differ by listing type; `price_per_meter` is stored when available.