"""
stat-mcmc module calculates intermediate statistics for monitoring state
"""

import statistics
import numpy as np
import cPickle as cpkl
import os
import scipy as sp

# unite stats for each output
class calcstats(object):
    """
    object class to set up and calculate summary statistics
    """
    def __init__(self, meta):
        self.meta = meta
    def update(self, ydata):
        stats = self.compute(ydata)
        self.meta.key.add_stats(self.meta.topdir, self.name, stats)

# statistics involving both log posterior probabilities and parameter values
class stat_both(calcstats):
    """
    calculates statistics that require both posterior probabilities and parameter values: log likelihood ratio and MAP parameter values
    """
    def __init__(self,meta):
        calcstats.__init__(self,meta)

        self.name = 'both'

        self.ll_stack = self.meta.postdist.lnlike(self.meta.logstack)
        self.ll_mapNz = self.meta.postdist.lnlike(self.meta.logmapNz)
        self.ll_expNz = self.meta.postdist.lnlike(self.meta.logexpNz)
        self.ll_intNz = self.meta.postdist.lnlike(self.meta.logintNz)
        self.ll_mleNz = self.meta.postdist.lnlike(self.meta.logmleNz)
        self.ll_samp = []
        self.mapvals,self.maps = [],[]

        self.llr_stack,self.llr_mapNz,self.llr_expNz,self.llr_intNz,self.llr_mleNz = [],[],[],[],[]

        outdict = {'ll_stack': self.ll_stack,
                  'll_mapNz': self.ll_mapNz,
                  'll_expNz': self.ll_expNz,
                  'll_intNz': self.ll_intNz,
                  'll_mleNz': self.ll_mleNz,
                  'llr_stack': np.array(self.llr_stack),
                  'llr_mapNz': np.array(self.llr_mapNz),
                  'llr_expNz': np.array(self.llr_expNz),
                  'llr_intNz': np.array(self.llr_intNz),
                  'llr_mleNz': np.array(self.llr_mleNz)
                   }
        with open(os.path.join(self.meta.topdir,'stat_both.p'),'wb') as statboth:
            cpkl.dump(outdict,statboth)

    def compute(self,ydata):

        self.probs = ydata['probs']
        self.chains = ydata['chains']

        where = np.unravel_index(np.argmax(self.probs),(self.meta.nwalkers,self.meta.ntimes))
        self.mapvals.append(self.chains[where])
        self.maps.append(self.probs[where])

        self.llr_stack = self.calclr(self.llr_stack,self.ll_stack)
        self.llr_mapNz = self.calclr(self.llr_mapNz,self.ll_mapNz)
        self.llr_expNz = self.calclr(self.llr_expNz,self.ll_expNz)

        if self.meta.logtrueNz is not None:
            self.calclr(self.ll_samp,0.)

        with open(os.path.join(self.meta.topdir,'stat_both.p'),'rb') as indict:
            outdict = cpkl.load(indict)

        outdict['llr_stack'] = np.array(self.llr_stack)
        outdict['llr_mapNz'] = np.array(self.llr_mapNz)
        outdict['llr_expNz'] = np.array(self.llr_expNz)
        outdict['ll_samp'] = np.array(self.ll_samp).flatten()/2.
        outdict['mapvals'] = np.array(self.mapvals)
        outdict['maps'] = np.array(self.maps)

        with open(os.path.join(self.meta.topdir,'stat_both.p'),'wb') as statboth:
            cpkl.dump(outdict,statboth)
        return

    # likelihood ratio test
    def calclr(self,var,ll):

        for w in xrange(self.meta.nwalkers):
            for x in xrange(self.meta.ntimes):
                ll_samp = self.probs[w][x]-self.meta.postdist.priorprob(self.chains[w][x])
                var.append(2.*(ll_samp-ll))
#                 self.llr_stack.append(2.*ll_samp-2.*self.ll_stack)
#                 self.llr_mapNz.append(2.*ll_samp-2.*self.ll_mapNz)
#                 self.llr_expNz.append(2.*ll_samp-2.*self.ll_expNz)
        return(var)

# statistics involving parameter values
class stat_chains(calcstats):
    """
    calculates statistics that need parameter values: variance, chi^2, KLD
    """
    def __init__(self, meta):
        calcstats.__init__(self, meta)

        self.name = 'chains'

        self.var_ls = []
        self.var_s = []
        self.vslogstack = None
        self.vslogmapNz = None
        self.vslogexpNz = None
        self.vsstack = None
        self.vsmapNz = None
        self.vsexpNz = None

        self.chi_ls = []
        self.chi_s = []
        self.cslogstack = None
        self.cslogmapNz = None
        self.cslogexpNz = None
        self.csstack = None
        self.csmapNz = None
        self.csexpNz = None

        self.kl_stackvtrue,self.kl_truevstack = None,None
        self.kl_mapNzvtrue,self.kl_truevmapNz = None,None
        self.kl_expNzvtrue,self.kl_truevexpNz = None,None
        self.kl_intNzvtrue,self.kl_truevintNz = None,None
        self.kl_mleNzvtrue,self.kl_truevmleNz = None,None
        self.kl_sampvtrue,self.kl_truevsamp = None,None

        if self.meta.logtrueNz is not None:
            vslogstack = self.meta.logstack-self.meta.logtrueNz
            self.vslogstack = np.dot(vslogstack,vslogstack)
            vslogmapNz = self.meta.logmapNz-self.meta.logtrueNz
            self.vslogmapNz = np.dot(vslogmapNz,vslogmapNz)
            vslogexpNz = self.meta.logexpNz-self.meta.logtrueNz
            self.vslogexpNz = np.dot(vslogexpNz,vslogexpNz)

            self.cslogstack = np.average((self.meta.logstack-self.meta.logtrueNz)**2)
            self.cslogmapNz = np.average((self.meta.logmapNz-self.meta.logtrueNz)**2)
            self.cslogexpNz = np.average((self.meta.logexpNz-self.meta.logtrueNz)**2)

            self.kl_stackvtrue,self.kl_truevstack = self.calckl(self.meta.logstack,self.meta.logtrueNz)
            self.kl_mapNzvtrue,self.kl_truevmapNz = self.calckl(self.meta.logmapNz,self.meta.logtrueNz)
            self.kl_expNzvtrue,self.kl_truevexpNz = self.calckl(self.meta.logexpNz,self.meta.logtrueNz)
            self.kl_intNzvtrue,self.kl_truevintNz = self.calckl(self.meta.logintNz,self.meta.logtrueNz)
            self.kl_mleNzvtrue,self.kl_truevmleNz = self.calckl(self.meta.logmleNz,self.meta.logtrueNz)
            self.kl_sampvtrue,self.kl_truevsamp = [],[]

        if self.meta.trueNz is not None:
            vsstack = meta.stack-meta.trueNz
            self.vsstack = np.dot(vsstack,vsstack)
            vsmapNz = meta.mapNz-meta.trueNz
            self.vsmapNz = np.dot(vsmapNz,vsmapNz)
            vsexpNz = meta.expNz-meta.trueNz
            self.vsexpNz = np.dot(vsexpNz,vsexpNz)

            self.csstack = np.average((self.meta.stack-self.meta.trueNz)**2)
            self.csmapNz = np.average((self.meta.mapNz-self.meta.trueNz)**2)
            self.csexpNz = np.average((self.meta.expNz-self.meta.trueNz)**2)

        outdict = {'vslogstack': self.vslogstack,
                   'vsstack': self.vsstack,
                   'vslogmapNz': self.vslogmapNz,
                   'vsmapNz': self.vsmapNz,
                   'vslogexpNz': self.vslogexpNz,
                   'vsexpNz': self.vsexpNz,
                   'cslogstack': self.cslogstack,
                   'csstack': self.csstack,
                   'cslogmapNz': self.cslogmapNz,
                   'csmapNz': self.csmapNz,
                   'cslogexpNz': self.cslogexpNz,
                   'csexpNz': self.csexpNz,
                   'kl_stackvtrue': self.kl_stackvtrue,
                   'kl_mapNzvtrue': self.kl_mapNzvtrue,
                   'kl_expNzvtrue': self.kl_expNzvtrue,
                   'kl_sampvtrue': self.kl_sampvtrue,
                   'kl_intNzvtrue': self.kl_intNzvtrue,
                   'kl_mleNzvtrue': self.kl_mleNzvtrue,
                   'kl_truevstack': self.kl_truevstack,
                   'kl_truevmapNz': self.kl_truevmapNz,
                   'kl_truevexpNz': self.kl_truevexpNz,
                   'kl_truevsamp': self.kl_truevsamp,
                   'kl_truevintNz': self.kl_truevintNz,
                   'kl_truevmleNz': self.kl_truevmleNz
              }

        with open(os.path.join(self.meta.topdir,'stat_chains.p'),'wb') as statchains:
            cpkl.dump(outdict,statchains)

    def compute(self, ydata):#ntimes*nwalkers*nbins

        self.ydata = ydata
        self.eydata = np.exp(self.ydata)
        y = np.swapaxes(self.ydata.T,0,1).T#nwalkers*nbins*ntimes
        ey = np.swapaxes(self.eydata.T,0,1).T#np.exp(y)

        if self.meta.logtrueNz is None:
            my = np.array([[[sum(by)/len(by)]*self.meta.ntimes for by in wy] for wy in y])#nwalkers*nbins*ntimes
            mey = np.array([[[sum(bey)/len(bey)]*self.meta.ntimes for bey in wey] for wey in ey])#nwalkers*nbins*ntimes
        else:
            my = np.array([[[k]*self.meta.ntimes for k in self.meta.logtrueNz]]*self.meta.nwalkers)#nwalkers*nbins*ntimes
            mey = np.array([[[k]*self.meta.ntimes for k in self.meta.trueNz]]*self.meta.nwalkers)#nwalkers*nbins*ntimes

            for w in xrange(self.meta.nwalkers):
                for x in xrange(self.meta.ntimes):
                    #ulog = np.exp(self.chains[w][x])
                    #ulogpz = ulog/sum(ulog)
                    #logpz = np.log(ulogpz)
                    pq,qp = self.calckl(self.ydata[w][x],self.meta.logtrueNz)
                    self.kl_sampvtrue.append(pq)
                    self.kl_truevsamp.append(qp)

        self.sy = np.swapaxes((y-my),1,2)#nwalkers*ntimes*nbins to #nwalkers*nbins*ntimes
        self.sey = np.swapaxes((ey-mey),1,2)

        self.var_ls = self.calcvar(self.var_ls,self.sy)
        self.var_s = self.calcvar(self.var_s,self.sey)
        self.chi_ls = self.calcchi(self.chi_ls,self.sy,self.ydata)
        self.chi_s = self.calcchi(self.chi_s,self.sey,self.eydata)

        with open(os.path.join(self.meta.topdir,'stat_chains.p'),'rb') as indict:
            outdict = cpkl.load(indict)

        outdict['kl_sampvtrue'] = np.array(self.kl_sampvtrue)
        outdict['kl_truevsamp'] = np.array(self.kl_truevsamp)
        #outdict['tot_var_ls'] = self.tot_var_ls
        #outdict['tot_var_s'] = self.tot_var_s
        outdict['var_ls'] = self.var_ls
        outdict['var_s'] = self.var_s
        #outdict['tot_chi_ls'] = self.tot_chi_ls
        #outdict['tot_chi_s'] = self.tot_chi_s
        outdict['chi_ls'] = self.chi_ls
        outdict['chi_s'] = self.chi_s

        with open(os.path.join(self.meta.topdir,'stat_chains.p'),'wb') as indict:
            cpkl.dump(outdict,indict)
            #print('after addition'+str(outdict))

#         return { 'vslogstack': self.vslogstack,
#                'vsstack': self.vsstack,
#                'vslogmapNz': self.vslogmapNz,
#                'vsmapNz': self.vsmapNz,
#                'vslogexpNz': self.vslogexpNz,
#                'vsexpNz': self.vsexpNz,
#                'tot_var_ls': self.tot_var_ls,
#                'tot_var_s': self.tot_var_s,
#                'var_ls': self.var_ls,
#                'var_s': self.var_s
#               }

    # variance of samples
    def calcvar(self,var,s):

        ans = np.average([[np.dot(s[w][i],s[w][i]) for i in xrange(len(s[w]))] for w in xrange(len(s))])
        var.append(ans)
#         var_ls = np.average([[np.dot(self.sy[w][i],self.sy[w][i]) for i in xrange(self.meta.ntimes)] for w in xrange(self.meta.nwalkers)])#/float(self.meta.nwalkers*self.meta.ntimes*self.meta.nbins)
#         var_s = np.average([[np.dot(self.sey[w][i],self.sey[w][i]) for i in xrange(self.meta.ntimes)] for w in xrange(self.meta.nwalkers)])#/float(self.meta.nwalkers*self.meta.ntimes*self.meta.nbins)
#         self.var_ls.append(var_ls)
#         self.var_s.append(var_s)
        #self.tot_var_ls = self.tot_var_ls+var_ls
        #self.tot_var_s = self.tot_var_s+var_s
        #print(self.meta.name+' var_ls='+str(self.var_ls))
        #print(self.meta.name+' var_s='+str(self.var_s))
        return(var)

    # chi^2 (or Wald test) of samples
    def calcchi(self,var,s,data):

        v = np.sum([np.average([statistics.variance(walk) for walk in data.T[b]]) for b in xrange(len(data.T))])#abs(np.linalg.det(np.cov(flatdata)))
        ans = np.average(s**2)/v
        var.append(ans)

#         flatdata = np.array([self.ydata.T[b].flatten() for b in xrange(self.meta.nbins)])
#         eflatdata = np.exp(flatdata)

#         vy = np.sum([np.average([statistics.variance(walk) for walk in self.ydata.T[b]]) for b in xrange(self.meta.nbins)])#abs(np.linalg.det(np.cov(flatdata)))
#         vey = np.sum([np.average([statistics.variance(walk) for walk in self.eydata.T[b]]) for b in xrange(self.meta.nbins)])#abs(np.linalg.det(np.cov(eflatdata)))

#         chi_ls = np.average(self.sy**2)/vy#np.average(sp.stats.chisquare(flatdata.T)[0])#float(self.meta.nwalkers*self.meta.ntimes*self.meta.nbins*vy)
#         chi_s = np.average(self.sey**2)/vey#np.average(sp.stats.chisquare(eflatdata.T)[0])#float(self.meta.nwalkers*self.meta.ntimes*self.meta.nbins*vey)
#         self.chi_ls.append(chi_ls)
#         self.chi_s.append(chi_s)
#         #self.tot_chi_ls = self.tot_chi_ls+chi_ls
#         #self.tot_chi_s = self.tot_chi_s+chi_s
#         print(self.meta.name+' chi_ls='+str(self.chi_ls))
#         print(self.meta.name+' chi_s='+str(self.chi_s))
        return(var)

    # KL Divergence test
    def calckl(self,lqn,lpn):
        pn = np.exp(lpn)*self.meta.bindifs
        qn = np.exp(lqn)*self.meta.bindifs
        p = pn/np.sum(pn)
        q = qn/np.sum(qn)
        logp = np.log(p)
        logq = np.log(q)
        klpq = np.sum(p*(logp-logq))
        klqp = np.sum(q*(logq-logp))
        return(round(klpq,3),round(klqp,3))

class stat_probs(calcstats):
    """
    calculates statistics requiring only probabilities:  log posterior probability for alternatives, variance of probabilities
    """
    def __init__(self, meta):
        calcstats.__init__(self, meta)
        #self.summary = 0
        self.name = 'probs'

#         # calculating log likelihood ratio test statistic for each relative to truth (and true relative to prior)
        if self.meta.logtrueNz is not None:
            self.lp_true = self.meta.postdist.lnprob(self.meta.logtrueNz)
            self.lik_true = self.meta.postdist.lnlike(self.meta.logtrueNz)
        else:
            self.lp_true = self.meta.postdist.lnprob(self.meta.mean)
            self.lik_true = self.meta.postdist.lnlike(self.meta.mean)

        self.lp_stack = self.meta.postdist.lnprob(self.meta.logstack)
        self.lp_mapNz = self.meta.postdist.lnprob(self.meta.logmapNz)
        self.lp_expNz = self.meta.postdist.lnprob(self.meta.logexpNz)

        self.var_y = []

    def compute(self, ydata):
        y = np.swapaxes(ydata,0,1).T
        var_y = sum([statistics.variance(y[w]) for w in xrange(self.meta.nwalkers)])/self.meta.nwalkers
        #self.llr_samp.append((2.*np.max(lik_y)-2.*self.ll_true))
        self.var_y.append(var_y)
        # self.summary = self.summary+var_y
        return { #'summary': self.summary,
                 'var_y': self.var_y,
                 'lp_true': self.lp_true,
                 'lp_stack': self.lp_stack,
                 'lp_mapNz': self.lp_mapNz,
                 'lp_expNz': self.lp_expNz
               }

class stat_fracs(calcstats):
    """
    calculates summary statistics on acceptance fractions
    """
    def __init__(self, meta):
        calcstats.__init__(self, meta)
        self.var_y = []
        self.name = 'fracs'
    def compute(self, ydata):
        y = ydata.T
        var_y = statistics.variance(y)
        self.var_y.append(var_y)
        return {'var_y': self.var_y}

class stat_times(calcstats):
    """
    calculates summary statistics on autocorrelation times
    """
    def __init__(self, meta):
        calcstats.__init__(self, meta)
        self.var_y = []
        self.name = 'times'
    def compute(self, ydata):
        y = ydata.T
        var_y = np.var(y)
        self.var_y.append(var_y)
        return {'var_y': self.var_y}

# calculate autocorrelation times since emcee sometimes fails
def cft(xtimes,lag):
    lent = len(xtimes)-lag
    allt = xrange(lent)
    ans = np.array([xtimes[t+lag]*xtimes[t] for t in allt])
    return ans

def cf(xtimes):#xtimes has ntimes elements
    cf0 = np.dot(xtimes,xtimes)
    allt = xrange(len(xtimes)/2)
    cf = np.array([sum(cft(xtimes,lag)[len(xtimes)/2:]) for lag in allt])/cf0
    return cf

def cfs(x,mode):#xbinstimes has nbins by ntimes elements
    if mode == 'walkers':
        xbinstimes = x
        cfs = np.array([sum(cf(xtimes)) for xtimes in xbinstimes])/len(xbinstimes)
    if mode == 'bins':
        xwalkerstimes = x
        cfs = np.array([sum(cf(xtimes)) for xtimes in xwalkerstimes])/len(xwalkerstimes)
    return cfs

def acors(xtimeswalkersbins,mode):
    if mode == 'walkers':
        xwalkersbinstimes = np.swapaxes(xtimeswalkersbins,1,2)#nwalkers by nbins by nsteps
        taus = np.array([1. + 2.*sum(cfs(xbinstimes,mode)) for xbinstimes in xwalkersbinstimes])#/len(xwalkersbinstimes)# 1+2*sum(...)
    if mode == 'bins':
        xbinswalkerstimes = xtimeswalkersbins.T#nbins by nwalkers by nsteps
        taus = np.array([1. + 2.*sum(cfs(xwalkerstimes,mode)) for xwalkerstimes in xbinswalkerstimes])#/len(xwalkersbinstimes)# 1+2*sum(...)
    return taus
