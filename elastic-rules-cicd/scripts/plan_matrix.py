#!/usr/bin/env python3
"""Emit an Azure DevOps matrix, one leg per deployment in a ring.

Used only by the optional matrix variant of the deploy stage, where you want
each deployment to appear as its own parallel job in the pipeline UI.

  python scripts/plan_matrix.py --ring 2

prints the matrix as a pipeline output variable:

  ##vso[task.setvariable variable=matrix;isOutput=true]{"acme-prod":{"deploymentId":"acme-prod"}}
"""

import argparse
import json
import sys

from common import filter_targets, load_targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ring", type=int, required=True)
    args = parser.parse_args()

    targets = filter_targets(load_targets(), ring=args.ring)
    if not targets:
        print(f"no deployments in ring {args.ring}", file=sys.stderr)
        return 1

    matrix = {}
    for target in targets:
        deployment = target["deployment_id"]
        matrix.setdefault(deployment, {"deploymentId": deployment})

    for deployment in sorted(matrix):
        spaces = [t["space_id"] for t in targets if t["deployment_id"] == deployment]
        print(f"{deployment}: {len(spaces)} space(s) -> {', '.join(sorted(spaces))}", file=sys.stderr)

    print(f"##vso[task.setvariable variable=matrix;isOutput=true]{json.dumps(matrix)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
