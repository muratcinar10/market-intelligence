
def bayesian(hit_rate,n,prior=.55,strength=20):
    return (hit_rate*n + prior*strength)/(n+strength)

def from_counts(success, fail):
    n=success+fail
    if n==0:
        return 55.0
    hr=success/n
    return round(100*bayesian(hr,n),1)
