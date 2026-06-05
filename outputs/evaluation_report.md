# ConfigForge AI Evaluation Report

- Total prompts: 20
- Success rate: 100.0%
- Passed without repair: 10
- Passed after repair: 10
- Failed: 0
- Average repairs per request: 0.55
- Average latency: 6.93 ms

## Repair Types

- MISSING_PERMISSION: 5
- MISSING_ROLE: 20
- PERMISSION_REFERENCES_MISSING_ROLE: 13
- MISSING_API_ENDPOINT: 2
- INVALID_FORM_ENDPOINT: 1
- DB_TABLE_MISSING_PRIMARY_KEY: 1
- RELATIONSHIP_REFERENCES_MISSING_TABLE: 1
- PREMIUM_RULE_MISSING: 1

## Quality Metrics

- Average consistency score: 95
- Average execution score: 96
- Average schema score: 94
- Average repairability score: 92

## Results

- #1 [product] crm-workspace: validation=passed, execution=passed, repairs=0, fault=None
- #2 [product] inventory-management-builder: validation=passed, execution=passed, repairs=0, fault=None
- #3 [product] hospital-management-builder: validation=passed, execution=passed, repairs=0, fault=None
- #4 [product] school-erp-builder: validation=passed, execution=passed, repairs=0, fault=None
- #5 [product] inventory-management-builder: validation=passed, execution=passed, repairs=0, fault=None
- #6 [product] food-delivery-builder: validation=passed, execution=passed, repairs=0, fault=None
- #7 [product] job-portal-builder: validation=passed, execution=passed, repairs=0, fault=None
- #8 [product] event-management-builder: validation=passed, execution=passed, repairs=0, fault=None
- #9 [product] learning-management-builder: validation=passed, execution=passed, repairs=0, fault=None
- #10 [product] project-management-builder: validation=passed, execution=passed, repairs=0, fault=None
- #11 [edge] generic-business-builder: validation=passed, execution=passed, repairs=1, fault=remove_permission
- #12 [edge] generic-business-builder: validation=passed, execution=passed, repairs=1, fault=remove_role
- #13 [edge] crm-workspace: validation=passed, execution=passed, repairs=1, fault=remove_endpoint
- #14 [edge] ecommerce-builder: validation=passed, execution=passed, repairs=1, fault=break_form_endpoint
- #15 [edge] hospital-management-builder: validation=passed, execution=passed, repairs=1, fault=remove_primary_key
- #16 [edge] generic-business-builder: validation=passed, execution=passed, repairs=1, fault=remove_relationship_table
- #17 [edge] school-erp-builder: validation=passed, execution=passed, repairs=1, fault=remove_premium_rule
- #18 [edge] saas-dashboard-builder: validation=passed, execution=passed, repairs=2, fault=remove_permission
- #19 [edge] job-portal-builder: validation=passed, execution=passed, repairs=1, fault=remove_role
- #20 [edge] inventory-management-builder: validation=passed, execution=passed, repairs=1, fault=remove_endpoint
