"""
awslimitchecker docs/build_generated_docs.py

Builds documentation that is generated dynamically from awslimitchecker.

The latest version of this package is available at:
<https://github.com/jantman/awslimitchecker>

################################################################################
Copyright 2015-2018 Jason Antman <jason@jasonantman.com>

    This file is part of awslimitchecker, also known as awslimitchecker.

    awslimitchecker is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    awslimitchecker is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with awslimitchecker.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/awslimitchecker> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""

import json
import logging
import os
import sys
import subprocess
from textwrap import dedent

my_dir = os.path.dirname(os.path.abspath(__file__))
os.environ['PYTHONPATH'] = os.path.join(my_dir, '..')
sys.path.insert(0, os.path.join(my_dir, '..'))

from awslimitchecker.checker import AwsLimitChecker
from awslimitchecker.metrics import MetricsProvider
from awslimitchecker.alerts import AlertProvider

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


def build_iam_policy(checker):
    logger.info("Beginning build of iam_policy.rst")
    # get the policy dict
    logger.info("Getting IAM Policy")
    policy = checker.get_required_iam_policy()
    # serialize as pretty-printed JSON
    policy_json = json.dumps(policy, sort_keys=True, indent=2)
    # indent each line by 4 spaces
    policy_str = ''
    for line in policy_json.split("\n"):
        policy_str += (' ' * 4) + line + "\n"
    doc = """
    .. -- WARNING -- WARNING -- WARNING
       This document is automatically generated by
       awslimitchecker/docs/build_generated_docs.py.
       Please edit that script, or the template it points to.

    .. _iam_policy:

    Required IAM Permissions
    ========================

    .. important::
       The required IAM policy output by awslimitchecker includes only the permissions
       required to check limits and usage. If you are loading
       :ref:`limit overrides <cli_usage.limit_overrides>` and/or
       :ref:`threshold overrides <cli_usage.threshold_overrides>` from S3, you will
       need to run awslimitchecker with additional permissions to access those objects.

    Below is the sample IAM policy from this version of awslimitchecker, listing the IAM
    permissions required for it to function correctly. Please note that in some cases
    awslimitchecker may cause AWS services to make additional API calls on your behalf
    (such as when enumerating ElasticBeanstalk resources, the ElasticBeanstalk service
    itself will make ``s3:ListBucket`` and ``s3:GetBucketLocation`` calls). The policy
    below includes only the bare minimum permissions for awslimitchecker to function
    properly, and does not include permissions for any side-effect calls made by AWS
    services that do not affect the results of this program.

    .. code-block:: json

    {policy_str}
    """
    doc = dedent(doc)
    doc = doc.format(policy_str=policy_str)
    fname = os.path.join(my_dir, 'source', 'iam_policy.rst')
    logger.info("Writing %s", fname)
    with open(fname, 'w') as fh:
        fh.write(doc)


def format_limits_for_service(limits):
    limit_info = ''
    # build a dict of the limits
    slimits = {}
    # track the maximum string lengths
    max_name = 0
    max_default_limit = 0
    for limit in limits.values():
        slimits[limit.name] = limit
        # update max string length for table formatting
        if len(limit.name) > max_name:
            max_name = len(limit.name)
        if len(str(limit.default_limit)) > max_default_limit:
            max_default_limit = len(str(limit.default_limit))
    # create the format string
    sformat = '{name: <' + str(max_name) + '} ' \
                                           '{ta: <15} {api: <7} ' \
                                           '{limit: <' + str(
        max_default_limit) + '}\n'
    # separator lines
    sep = ('=' * max_name) + ' =============== ======= ' + \
          ('=' * max_default_limit) + "\n"
    # header
    limit_info += sep
    limit_info += sformat.format(
        name='Limit', limit='Default', api='API', ta='Trusted Advisor'
    )
    limit_info += sep
    # limit lines
    for lname, limit in sorted(slimits.iteritems()):
        limit_info += sformat.format(
            name=lname, limit=str(limit.default_limit),
            ta='|check|' if limit.ta_limit is not None else '',
            api='|check|' if (
                    limit.api_limit is not None or limit.has_resource_limits()
            ) else ''
        )
    # footer
    limit_info += sep
    limit_info += "\n"
    return limit_info


def limits_for_ec2():
    limit_info = '.. _limits.EC2:\n\n'
    limit_info += "EC2\n---\n\n"
    limit_info += dedent("""
    As of October 2019, the "standard" EC2 regions use the new
    `vCPU-based limits <https://aws.amazon.com/blogs/compute/preview-vcpu-based-
    instance-limits/>`__, while the China (``cn-``) and GovCloud (``us-gov-``)
    regions still use the old per-instance-type limits. Please see the sections
    for either :ref:`limits.ec2-standard` or :ref:`limits.ec2-nonvcpu` for
    details.
    
    """)
    limit_info += '.. _limits.ec2-standard:\n\n'
    limit_info += "EC2 - Standard Regions\n"
    limit_info += "----------------------\n"
    limit_info += "\n" + dedent("""
    **Note on On-Demand vs Reserved Instances:** The EC2 limits for
    "Running On-Demand" EC2 Instances apply only to On-Demand instances,
    not Reserved Instances. If you list all EC2 instances that are
    running in the Console or API, you'll get back instances of all types
    (On-Demand, Reserved, etc.). The value that awslimitchecker reports
    for Running On-Demand Instances current usage will *not* match the
    number of instances you see in the Console or API.
    
    **Important:** The limits for Running On-Demand Instances are now measured
    in vCPU count per instance family, not instance count per instance type. 
    """) + "\n"
    limit_info += "\n"
    limit_info += format_limits_for_service(
        AwsLimitChecker(region='us-east-1').get_limits()['EC2']
    )
    limit_info += '.. _limits.ec2-nonvcpu:\n\n'
    limit_info += "EC2 - China and GovCloud\n"
    limit_info += "------------------------\n"
    limit_info += "\n" + dedent("""
        **Note on On-Demand vs Reserved Instances:** The EC2 limits for
        "Running On-Demand" EC2 Instances apply only to On-Demand instances,
        not Reserved Instances. If you list all EC2 instances that are
        running in the Console or API, you'll get back instances of all types
        (On-Demand, Reserved, etc.). The value that awslimitchecker reports
        for Running On-Demand Instances current usage will *not* match the
        number of instances you see in the Console or API.
        """) + "\n"
    limit_info += "\n"
    fname = os.path.join(my_dir, 'source', 'ec2_nonvcpu_limits.txt')
    with open(fname, 'r') as fh:
        limit_info += fh.read()
    limit_info += "\n\n"
    return limit_info


def build_limits(checker):
    logger.info("Beginning build of limits.rst")
    logger.info("Getting Limits")
    limit_info = ''
    limits = checker.get_limits()
    # this is a bit of a pain, because we need to know string lengths to build the table
    for svc_name in sorted(limits):
        if svc_name == 'EC2':
            limit_info += limits_for_ec2()
            continue
        limit_info += '.. _limits.%s:\n\n' % svc_name
        limit_info += svc_name + "\n"
        limit_info += ('-' * (len(svc_name)+1)) + "\n"
        if svc_name == 'Route53':
            limit_info += "\n" + dedent("""
            **Note on Route53 Limits:** The Route53 limit values (maxima) are
            set per-hosted zone, and can be increased by AWS support per-hosted
            zone. As such, each zone may have a different limit value.
            """) + "\n"
        limit_info += "\n"
        limit_info += format_limits_for_service(limits[svc_name])

    doc = """
    .. -- WARNING -- WARNING -- WARNING
       This document is automatically generated by
       awslimitchecker/docs/build_generated_docs.py.
       Please edit that script, or the template it points to.

    .. _limits:

    Supported Limits
    ================

    The section below lists every limit that this version of awslimitchecker knows
    how to check, and its hard-coded default value (per AWS documentation).

    **Limits with a** |check| **in the "Trusted Advisor" column are comfirmed as being
    updated by Trusted Advisor.** Note that so long as the Service and Limit names used by
    Trusted Advisor (and returned in its API responses) exactly match those
    shown below, all limits listed in Trusted Advisor "Service Limit" checks
    should be automatically used by awslimitchecker. However, limits marked here
    with a |check| were detected as being returned by Trusted Advisor as of the
    last release. Note that not all accounts can access Trusted Advisor, or can
    access all limits known by Trusted Advisor.

    **Limits with a** |check| **in the "API" column can be retrieved directly from
    the corresponding Service API**; this information should be the most accurate
    and up-to-date, as it is retrieved directly from the service that evaluates
    and enforces limits. Limits retrieved via service API take precedence over
    Trusted Advisor and default limits.

    {limit_info}

    .. |check| unicode:: 0x2714 .. heavy check mark
    """
    doc = dedent(doc)
    doc = doc.format(limit_info=limit_info)
    fname = os.path.join(my_dir, 'source', 'limits.rst')
    logger.info("Writing %s", fname)
    with open(fname, 'w') as fh:
        fh.write(doc)


def build_runner_examples():
    logger.info("Beginning build of runner examples")
    # read in the template file
    with open(os.path.join(my_dir, 'source', 'cli_usage.rst.template'), 'r') as fh:
        tmpl = fh.read()
    # examples to run
    examples = {
        'help': ['awslimitchecker', '--help'],
        'list_limits': ['awslimitchecker', '-l'],
        'list_defaults': ['awslimitchecker', '--list-defaults'],
        'skip_ta': ['awslimitchecker', '-l', '--skip-ta'],
        'show_usage': ['awslimitchecker', '-u'],
        'list_services': ['awslimitchecker', '-s'],
        'limit_overrides': [
            'awslimitchecker',
            '-L',
            '"AutoScaling/Auto Scaling groups"=321',
            '--limit="AutoScaling/Launch configurations"=456',
            '-l',
        ],
        'check_thresholds': ['awslimitchecker', '--no-color'],
        'check_thresholds_custom': ['awslimitchecker', '-W', '97',
                                    '--critical=98', '--no-color'],
        'iam_policy': ['awslimitchecker', '--iam-policy'],
        'list_metrics': ['awslimitchecker', '--list-metrics-providers'],
        'list_alerts': ['awslimitchecker', '--list-alert-providers'],
    }
    results = {}
    # run the commands
    for name, command in examples.items():
        cmd_str = ' '.join(command)
        logger.info("Running: %s", cmd_str)
        try:
            output = subprocess.check_output(command)
        except subprocess.CalledProcessError as e:
            output = e.output
        results[name] = format_cmd_output(cmd_str, output, name)
        results['%s-output-only' % name] = format_cmd_output(None, output, name)
    results['metrics-providers'] = ''
    for m in MetricsProvider.providers_by_name().keys():
        results['metrics-providers'] += '* :py:class:`~awslimitchecker.' \
                                        'metrics.%s.%s`\n' % (m.lower(), m)
    results['alert-providers'] = ''
    for m in AlertProvider.providers_by_name().keys():
        results['alert-providers'] += '* :py:class:`~awslimitchecker.' \
                                        'alerts.%s.%s`\n' % (m.lower(), m)
    results['limit-override-json'] = dedent("""
        {
            "AutoScaling": {
                "Auto Scaling groups": 321,
                "Launch configurations": 456
            }
        }
    """)
    results['threshold-override-json'] = dedent("""
        {
            "S3": {
                "Buckets": {
                    "warning": {
                        "percent": 97
                    },
                    "critical": {
                        "percent": 99
                    }
                }
            },
            "EC2": {
                "Security groups per VPC": {
                    "warning": {
                        "percent": 80,
                        "count": 800
                    },
                    "critical": {
                        "percent": 90,
                        "count": 900
                    }
                },
                "VPC security groups per elastic network interface": {
                    "warning": {
                        "percent": 101
                    },
                    "critical": {
                        "percent": 101
                    }
                }
            }
        }
    """)
    for x in ['limit-override-json', 'threshold-override-json']:
        tmp = ''
        for line in results[x].split('\n'):
            if line.strip() == '':
                continue
            tmp += '    %s\n' % line
        results[x] = tmp
    tmpl = tmpl.format(**results)

    # write out the final .rst
    with open(os.path.join(my_dir, 'source', 'cli_usage.rst'), 'w') as fh:
        fh.write(tmpl)
    logger.critical("WARNING - some output may need to be fixed to provide good examples")


def format_cmd_output(cmd, output, name):
    """format command output for docs"""
    if cmd is None:
        formatted = ''
    else:
        formatted = '.. code-block:: console\n\n'
        formatted += '   (venv)$ {c}\n'.format(c=cmd)
    lines = output.split("\n")
    if name != 'help':
        for idx, line in enumerate(lines):
            if len(line) > 100:
                lines[idx] = line[:100] + ' (...)'
        if len(lines) > 12:
            tmp_lines = lines[:5] + ['(...)'] + lines[-5:]
            if cmd is not None and (' -l' in cmd or ' --list-defaults' in cmd):
                # find a line that uses a limit from the API,
                #  and a line with None (unlimited)
                api_line = None
                none_line = None
                for line in lines:
                    if '(API)' in line:
                        api_line = line
                        break
                for line in lines:
                    if line.strip().endswith('None'):
                        none_line = line
                        break
                tmp_lines = lines[:5]
                if api_line not in tmp_lines and api_line is not None:
                    tmp_lines = tmp_lines + ['(...)'] + [api_line]
                if none_line not in tmp_lines and none_line is not None:
                    tmp_lines = tmp_lines + ['(...)'] + [none_line]
                tmp_lines = tmp_lines + ['(...)'] + lines[-5:]
            lines = tmp_lines
    for line in lines:
        if line.strip() == '':
            continue
        if (
            name == 'check_thresholds_custom' and
            'VPC security groups per elastic network interface' in line
        ):
            continue
        formatted += '   ' + line + "\n"
    formatted += '\n'
    return formatted


def build_docs():
    """
    Trigger rebuild of all documentation that is dynamically generated
    from awslimitchecker.
    """
    if os.environ.get('CI', None) is not None:
        print("Not building dynamic docs in CI environment")
        raise SystemExit(0)
    region = os.environ.get('AWS_DEFAULT_REGION', None)
    if region is None:
        raise SystemExit("ERROR: Please export AWS_DEFAULT_REGION")
    logger.info("Beginning build of dynamically-generated docs")
    logger.info("Instantiating AwsLimitChecker")
    c = AwsLimitChecker(region=region)
    build_iam_policy(c)
    build_limits(c)
    build_runner_examples()


if __name__ == "__main__":
    build_docs()
