"""Implements a hill climbing algorithm approach to optimize functions"""
import numpy

def climb_continuous(func,start,initstepsize=None,accel=1.2,delta=1e-3):
    """Maximizes func, a function on continuous input, by hill-climbing.
    
    func - a function on n continuous inputs that returns a value to be maximized.
        func's inputs should be positional arguments.
    start - an iterable of length n of starting values.
    initstepsize - an iterable of length n of starting step sizes for each input.
        Defaults to a vector of all 1's.
    accel - "acceleration" to use in hill-climbing.
    delta - a measure of the total step size below which we will consider ourselves done
    """
    iterations=0
    # Set up initial conditions
    N = len(start)
    if initstepsize is None:
        initstepsize = numpy.ones(N)
        stepsize = numpy.ones(N)
    else:
        stepsize = numpy.array(initstepsize,dtype=float)
        initstepsize = numpy.array(initstepsize,dtype=float)
    candidates = numpy.array([-accel,-1/accel,1/accel,accel])
    currentpoint = numpy.array(start)
    currentval = func(*start)
    # Loop until our step size is small enough to stop
    while numpy.sqrt(sum((stepsize/initstepsize)**2)) > delta*numpy.sqrt(N):
        iterations += 1
        # Iterate over each coordinate
        for i in range(N):
            basis = numpy.identity(N)[i]
            best,bestval,bestc = None,currentval,None
            # Try each of the step options and find the best one
            for c in candidates:
                temp = currentpoint + c*stepsize[i]*basis
                try:
                    tempval = func(*temp)
                    if tempval > bestval:
                        best,bestval,bestc = temp,tempval,c
                except ValueError: # Out of func's domain
                    pass
            # If we didn't improve, reduce our step size. Else move.
            if best is None:
                stepsize[i] = stepsize[i]/accel
            else:
                currentpoint,currentval = best,bestval
                stepsize[i] = stepsize[i]*bestc
    print(iterations)
    return tuple(currentpoint)

def climb_discrete(func,start,stepsize=None):
    """Maximizes func, a function on discrete input, by hill-climbing.
    
    func - a function on n continuous inputs that returns a value to be maximized.
        func's inputs should be positional arguments.
    start - an iterable of length n of starting values.
    stepsize - an iterable of length n of step sizes for each input. Defaults to
        a vector of all 1's.
    """
    # Set up initial conditions
    N = len(start)
    if stepsize is None:
        stepsize = numpy.ones(N)
    else:
        stepsize = numpy.array(stepsize)
    currentpoint = numpy.array(start)
    currentval = func(*start)
    # Loop until our step size is small enough to stop
    improved = True
    while improved:
        improved = False
        ident = numpy.identity(N)
        steps = [stepsize[i]*ident[i] for i in range(N)]
        steps += [-stepsize[i]*ident[i] for i in range(N)]
        best,bestval = None,currentval
        for s in steps:
            temp = currentpoint + s
            try:
                tempval = func(*temp)
                if tempval > bestval:
                    best,bestval = temp,tempval
            except ValueError: #Out of func's domain
                pass
        # If we improved, reset our current point and continue
        if best is not None:
            currentpoint,currentval = best,bestval
            improved = True
    return tuple(currentpoint)
            
            

if __name__=='__main__':
    import time
    def f(*args):
        if min(args)<0:
            raise ValueError()
        v = 0
        for i in range(len(args)):
            v -= (numpy.sqrt(args[i])-numpy.sqrt(i+1))**2
        return v
    start = (0,0,0,0,0,0,0)
    step = (1,1,1,1,1,1,10)
    end = climb_continuous(f,start,initstepsize=step)
    print(end)
    print(f(*end))
    end = climb_discrete(f,start,stepsize=step)
    print(end)
    print(f(*end))