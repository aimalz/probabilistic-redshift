"""
per-mcmc module is variable object for MCMC sub-runs
"""

import os
import statistics
import timeit
import psutil
import numpy as np

import statmcmc as stats

def burntest(outputs,run):# of dimensions nwalkers*miniters
    """test whether burning in or done with that, true if burning in"""
    print('testing burn-in condition')

    lnprobs = outputs['probs']
    lnprobs = np.swapaxes(lnprobs,0,1).T
    varprob = sum([statistics.variance(w) for w in lnprobs])/run.meta.nwalkers
    difprob = statistics.median([(lnprobs[w][0]-lnprobs[w][-1])**2 for w in xrange(run.meta.nwalkers)])

    if difprob > varprob:
        print(run.meta.name+' burning-in '+str(difprob)+' > '+str(varprob))
    else:
        print(run.meta.name+' post-burn '+str(difprob)+' < '+str(varprob))

    return(difprob > varprob)

class pertest(object):
    """
    class object for MCMC state
    define class per initialization of MCMC
    will be changing this object at each iteration as it encompasses state
    """

    def __init__(self, meta):

        print('defining setup object methods')
        self.meta = meta
        self.vals = self.meta.ivals
        self.sampler = self.meta.sampler
        self.burns = 0
        self.runs = 0

        with open(self.meta.calctime,'a') as calctimer:
            calctimer.write(str(timeit.default_timer())+' icalc \n')

        # what outputs of emcee will we be saving?
        self.stats = [ #stats.stat_both(self.meta),
                       stats.stat_chains(self.meta),
                       stats.stat_probs(self.meta),
#                        stats.stat_fracs(self.meta),
                       stats.stat_times(self.meta) ]

    # TO DO: change emcee parameters to save less data to reduce i/o and storage
    def sampling(self):
        """sample with emcee and provide output"""
        sampler = self.meta.sampler
        ivals = self.vals
        miniters = self.meta.miniters
        thinto = self.meta.thinto
        # ntimes = self.meta.ntimes
        start_time = timeit.default_timer()
        sampler.reset()
        print 'running mcmc'
        pos, prob, state = sampler.run_mcmc(ivals,miniters,thin=thinto)
        print 'done running mcmc'
        ovals = [walk[-1] for walk in sampler.chain]
        chains = sampler.chain#nsteps*nwalkers*nbins
        probs = sampler.lnprobability#nsteps*nwalkers
        fracs = sampler.acceptance_fraction#nwalkers
        times = stats.acors(chains,self.meta.mode)#sampler.acor#get_autocorr_time()#nwalkers#sampler.get_autocorr_time(window = ntimes/2)#nbins
        both = {'probs':probs,'chains':chains}
        outputs = { 'times':times,
                    'fracs':fracs,
                    'probs':probs,
                    'chains':chains,
                    'both':both }
        elapsed = timeit.default_timer() - start_time
        self.vals = ovals
        self.outputs = outputs
        self.elapsed = elapsed

        return(outputs,elapsed)

    def sampnsave(self,r,burnin):
        """run one sampling, store new key and state, calculate stats"""
        self.key = self.meta.key.add(r=r, burnin=burnin)

        (outputs,elapsed) = self.sampling()

        self.key.store_state(self.meta.topdir, outputs)

        if self.meta.plotonly == 0:
            if burnin == False:
                self.savestats()
        if self.meta.plotonly == 1:
            with open(os.path.join(self.meta.topdir,'iterno.p')) as where:
                iterno = cpkl.load(where)
            if r >= iterno-self.meta.factor:
                self.savestats()

        # store the iteration number, so everyone knows how many iterations have been completed
        self.key.store_iterno(self.meta.topdir, self.runs)
        #print ('s_run={}, dist={}'.format(self.s_run, self.s_run.dist))
        self.meta.dist.complete_chunk(self.key)

        # record time of calculation for monitoring progress
        with open(self.meta.calctime,'a') as calctimer:
            process = psutil.Process(os.getpid())
            calctimer.write(str(timeit.default_timer())+' '+str(self.key)+' '+str(elapsed)+'\n')#'' mem:'+str(process.get_memory_info())+'\n')
            calctimer.close()

        return outputs

    def savestats(self):
        for stat in self.meta.stats:
            stat.update(self.outputs[stat.name])
        return

    def preburn(self, b):
        outputs = self.sampnsave(b,burnin=True)
        return outputs

    def atburn(self, b, outputs):
        """once burn-in complete, know total number of runs remaining"""
        print(str(b*self.meta.miniters)+' iterations of burn-in for '+self.meta.name)
        self.nsteps = b+self.meta.factor-1#*b+1
        self.maxiters = self.nsteps*self.meta.miniters
        self.alliternos = range(0,self.maxiters)
        self.alltimenos = range(0,self.maxiters/self.meta.thinto,self.meta.thinto)
        self.key.store_state(self.meta.topdir, outputs)
        self.key.store_iterno(self.meta.topdir, self.runs)
        return

    def postburn(self, p):
        self.sampnsave(p,burnin=False)
        return

    def samplings(self):
        """sample until burn-in complete, then do specified number of runs before finishing"""
        # may add ability to pick up where left off
        # if os.path.exists(self.statename):
        #   self = self.state()
        # else:
        if self.meta.plotonly == False:
            outputs = self.preburn(self.burns)
            print('zeroth run done for '+self.meta.name)

            while burntest(outputs,self):
                yield self
                self.burns += 1
                self.runs += 1
                outputs = self.preburn(self.runs)
            else:
                self.atburn(self.runs, outputs)
                while self.runs <= self.nsteps:
                    yield self
                    self.runs += 1
                    self.postburn(self.runs)
            return
        else:
            while self.runs <= self.meta.iterno:
                tempkey = self.meta.key.add(r=self.runs,burnin=False)
                self.meta.dist.complete_chunk(tempkey)
                yield self
                self.runs += 1
                print('tempkey '+str(tempkey))
            return
