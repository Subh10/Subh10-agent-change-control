import argparse, json
from .models import ChangePlan
from .policy import evaluate

def main():
    parser = argparse.ArgumentParser(description="Evaluate a proposed database change locally")
    parser.add_argument("--agent", default="demo-agent")
    parser.add_argument("--database", default="demo-postgres")
    parser.add_argument("--environment", default="production")
    parser.add_argument("--sql", required=True)
    parser.add_argument("--idempotency-key", default="local-demo-key-0001")
    args = parser.parse_args()
    plan = ChangePlan(agent_id=args.agent, database_id=args.database,
                      environment=args.environment, sql=args.sql,
                      idempotency_key=args.idempotency_key)
    print(json.dumps(evaluate(plan).model_dump(mode="json"), indent=2))

if __name__ == "__main__": main()
