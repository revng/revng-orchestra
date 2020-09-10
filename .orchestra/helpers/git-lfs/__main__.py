from __future__ import division, print_function, unicode_literals

import argparse
import sys

from __init__ import fetch

p = argparse.ArgumentParser()
p.add_argument('git_repo', nargs='?', default='.',
               help="if it's bare you need to provide a checkout_dir")
p.add_argument('checkout_dir', nargs='?')
p.add_argument('-v', '--verbose', action='count', default=0)
p.add_argument('-o', '--only', action='append')
args = p.parse_args()

sys.exit(0 if fetch(args.git_repo, args.checkout_dir, args.verbose, args.only) else 1)
