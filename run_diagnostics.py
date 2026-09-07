import sys
from src.services.startup_validator import run_startup_validation

def main():
    try:
        report = run_startup_validation()
        for check in report['checks']:
            if check['status'] != 'HEALTHY':
                print(f"  [{check['status']}] {check['check']}: {check['detail']}")
        
        if report['overall'] == 'CRITICAL':
            sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"  [CRITICAL] Exception during validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
