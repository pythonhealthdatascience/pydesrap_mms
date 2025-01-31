"""Helper functions.

Other helpful functions used in the code that do not set up or run
the simulation model.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:
    mean, std_dev, ci_lower, ci_upper = summary_stats(data)
"""
import numpy as np
import scipy.stats as st


def summary_stats(data):
    """
    Calculate mean, standard deviation and 95% confidence interval (CI).

    Arguments:
        data (pd.Series):
            Data to use in calculation.

    Returns:
        tuple: (mean, standard deviation, CI lower, CI upper).
    """
    mean = data.mean()
    count = len(data)

    # Cannot calculate some metrics if there is only 1 sample in data
    if count == 1:
        std_dev = np.nan
        ci_lower = np.nan
        ci_upper = np.nan
    else:
        std_dev = data.std()
        # Calculation of CI uses t-distribution, which is suitable for
        # smaller sample sizes (n<30)
        ci_lower, ci_upper = st.t.interval(
            confidence=0.95,
            df=count-1,
            loc=mean,
            scale=st.sem(data))

    return mean, std_dev, ci_lower, ci_upper
