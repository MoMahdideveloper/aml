# CSV import operator guide

## Templates (headers)

**Customers:** `name,email,phone,budget_min,budget_max,customer_type,status`  
**Properties:** `title,address,property_type,price,bedrooms,bathrooms,file_code,listing_type`  
**Deals:** `property_id,customer_id,agent_id,status,offer_amount` (or `property_file_code` / `customer_email`)

## Limits
2 MB, 500 rows, 40 columns, UTF-8 CSV.

## Flow
Upload → map columns → preview → review duplicates → execute → download errors → optional guarded rollback.

## Duplicate rules
- Customer: exact email or phone  
- Property: file_code or normalized address  
- Deal: same property + customer + status  
Possible duplicates require explicit **Import as new** or default **Skip**.

## Rollback
Soft-deletes only records created by that batch that have no dependent deals (for customers/properties). Never deletes pre-existing data.
