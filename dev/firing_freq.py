#import brian_no_units
from numpy import array
from brian import *
import time

from brian.library.IF import *
from brian.library.synapses import *

import matplotlib as mpl
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import matplotlib.pyplot as plt

import pickle
def minimal_example():
    # Neuron model parameters
    Vr = -70 * mV
    Vt = -55 * mV
    taum = 10 * ms
    taupsp = 0.325 * ms
    weight = 4.86 * mV
    # Neuron model
    equations = Equations('''
        dV/dt = (-(V-Vr)+x)*(1./taum)                        : volt
        dx/dt = (-x+y)*(1./taupsp)                               : volt
        dy/dt = -y*(1./taupsp)+25.27*mV/ms+(39.24*mV/ms**0.5)*xi : volt
        ''')

    # Neuron groups
    P = NeuronGroup(N=2000, model=equations,
                  threshold=Vt, reset=Vr, refractory=1 * ms)
#    P = NeuronGroup(N=1000, model=(dV,dx,dy),init=(0*volt,0*volt,0*volt),
#                  threshold=Vt,reset=Vr,refractory=1*ms)

    Pinput = PulsePacket(t=10 * ms, n=85, sigma=1 * ms)
    # The network structure
    Pgp = [ P.subgroup(100) for i in range(20)]
    C = Connection(P, P, 'y',delay=5*ms)
    for i in range(19):
        C.connect_full(Pgp[i], Pgp[i + 1], weight)
    Cinput = Connection(Pinput, P, 'y')
    Cinput.connect_full(Pinput, Pgp[0], weight)
    # Record the spikes
    Mgp = [SpikeMonitor(p, record=True) for p in Pgp]
    Minput = SpikeMonitor(Pinput, record=True)
    monitors = [Minput] + Mgp
    # Setup the network, and run it
    P.V = Vr + rand(len(P)) * (Vt - Vr)
    run(90 * ms)
    # Plot result
    raster_plot(showgrouplines=True, *monitors)
    show()


# DEFAULT PARAMATERS FOR SYNFIRE CHAIN
# Approximates those in Diesman et al. 1999
model_params = Parameters(
    # Simulation parameters
    dt=0.1 * ms,
    duration=90 * ms,
    # Neuron model parameters
    taupsp=0.325 * ms,
    Vt= -55 * mV,
    Vr= -70 * mV,
    abs_refrac=1 * ms,
    we=34.7143,
    wi=-34.7143,
    psp_peak=0.14 * mV,
    # Noise parameters
    noise_neurons=20000,
    noise_exc=0.88,
    noise_inh=0.12,
    noise_exc_rate=2 * Hz,
    noise_inh_rate=12.5 * Hz,
    computed_model_parameters="""
    noise_mu = noise_neurons * (noise_exc * noise_exc_rate - noise_inh * noise_inh_rate ) * psp_peak * we
    noise_sigma = (noise_neurons * (noise_exc * noise_exc_rate + noise_inh * noise_inh_rate ))**.5 * psp_peak * we
    """
    )

# MODEL FOR SYNFIRE CHAIN
# Excitatory PSPs only
def Model(p):
    equations = Equations('''
        dVe/dt = (-(Ve-p.Vr)+x)*(1./p.taum)                        : volt
        dx/dt = (-x+y)*(1./p.taupsp)                               : volt
        dy/dt = -y*(1./p.taupsp)+25.27*mV/ms+(39.24*mV/ms**0.5)*xi : volt
        ''')
    return Parameters(model=equations, threshold=p.Vt, reset=p.Vr, refractory=p.abs_refrac)

default_params = Parameters(
    # Network parameters
    num_layers=10,
    neurons_per_layer_e=110, #change this to obtain figure 4(a:80,b:90,c:100,d:110)
    neurons_per_layer_i=15,
    neurons_in_input_layer=100,
    total_neurons_e = 1100,
    total_neurons_i = 150,
    neuron_multiply = 1,
    # Initiating burst parameters
    initial_burst_t=50 * ms,
    initial_burst_a=85,
    initial_burst_sigma=1 * ms,
    # Spareness of connections
    pr = 1,
    # Membrane time constant
    taum=10 * ms,
    # these values are recomputed whenever another value changes
    #computed_network_parameters="""
    #total_neurons = neurons_per_layer * num_layers
    #""",
    # plus we also use the default model parameters
    ** model_params
    )

# DEFAULT NETWORK STRUCTURE
# Single input layer, multiple chained layers
class DefaultNetwork(Network):
    def __init__(self, pe, pi):
        # define groups
        chaingroup_e = NeuronGroup(N=pe.total_neurons, **Model(pe))
        chaingroup_i = NeuronGroup(N=pi.total_neurons, **Model(pi)) 
        
        inputgroup = PulsePacket(pe.initial_burst_t, pe.neurons_in_input_layer, pe.initial_burst_sigma)

        print "Total neurons excitatory= ",pe.total_neurons,"\n"
        print "Total neurons inhibitory= ",pi.total_neurons,"\n"
        
        unscaled_E = int(pe.neurons_per_layer)
        print "nE unscaled = ",unscaled_E,"\n"
        
        scaled_E = int(pe.neurons_per_layer_e * pe.neuron_multiply)
        print "nE scaled = ",scaled_E,"\n"
        
        unscaled_I = int(pi.neurons_per_layer)
        print "nI unscaled = ",unscaled_I,"\n"
        
        scaled_I = int(pi.neurons_per_layer_i * pe.neuron_multiply)
        print "nI scaled = ",scaled_I,"\n"
        
        layer_E = [ chaingroup_e.subgroup(unscaled_E) if i < (pe.num_layers-1) else chaingroup_e.subgroup(scaled_E) for i in range(pe.num_layers) ]
        
        layer_I = [ chaingroup_i.subgroup(unscaled_I) if i < (pi.num_layers-1) else chaingroup_i.subgroup(scaled_I) for i in range(pi.num_layers) ]

        
        # connections
        chainconnect_ee = Connection(chaingroup_e, chaingroup_e, 2,delay=0*ms)
        chainconnect_ei = Connection(chaingroup_e, chaingroup_i, 2,delay=0*ms)
        chainconnect_ii = Connection(chaingroup_i, chaingroup_i, 2,delay=0*ms)
        chainconnect_ie = Connection(chaingroup_i, chaingroup_e, 2,delay=0*ms)
        '''
        for i in range(p.num_layers - 1):
            chainconnect.connect_full(layer_E[i], layer_E[i + 1], p.psp_peak * p.we)
            chainconnect.connect_full(layer_E[i], layer_I[i + 1], p.psp_peak * p.we)
            chainconnect.connect_full(layer_I[i], layer_E[i + 1], p.psp_peak * p.wi)
            chainconnect.connect_full(layer_I[i], layer_I[i + 1], p.psp_peak * p.wi)    
        '''    
        # connect_random is same as connect_full with p.pr 1
        for i in range(pe.num_layers - 1):
            chainconnect_ee.connect_random(layer_E[i], layer_E[i + 1], sparseness = pe.pr, weight = p.psp_peak * pe.we)
            chainconnect_ei.connect_random(layer_E[i], layer_I[i + 1], sparseness = pe.pr, weight = p.psp_peak * pe.we)
            chainconnect_ie.connect_random(layer_I[i], layer_E[i + 1], sparseness = pi.pr, weight = p.psp_peak * pi.wi)
            chainconnect_ii.connect_random(layer_I[i], layer_I[i + 1], sparseness = pi.pr, weight = p.psp_peak * pi.wi)
                          
        inputconnect_E = Connection(inputgroup, layer_E[0], 2)
        inputconnect_E.connect_full(weight = pe.psp_peak * pe.we)
        inputconnect_I = Connection(inputgroup, layer_I[0], 2)
        inputconnect_I.connect_full(weight = pe.psp_peak * pe.we)
        
        # monitors
        chainmon_E = [SpikeMonitor(g, True) for g in layer_E]
        chainmon_I = [SpikeMonitor(g, True) for g in layer_I]
        inputmon = SpikeMonitor(inputgroup, True)
        mon_E = [inputmon] + chainmon_E
        mon_I = [inputmon] + chainmon_I
        # network
        Network.__init__(self, chaingroup_e, chaingroup_i, inputgroup, chainconnect_ee, chainconnect_ei, chainconnect_ii, chainconnect_ie, inputconnect_E, inputconnect_I, mon_E, mon_I)
        # add additional attributes to self
        self.mon_E = mon_E
        self.mon_I = mon_I
        self.chaingroup_e = chaingroup_e
        self.chaingroup_i = chaingroup_i
        self.layer_E = layer_E
        self.layer_I = layer_I
        self.pe = pe
        self.pi = pi

    def prepare(self):
        Network.prepare(self)
        self.reinit()

    def reinit(self, pe=None, pi=None):
        Network.reinit(self)
        #print("params after reinit",self.params)
        qe = self.pe
        qi = self.pi
        if pe is None: pe = qe
        if pi is None: pi = qi
        #print("p.wi",p.wi)
        self.inputgroup.generate(pe.initial_burst_t, pe.initial_burst_a, pe.initial_burst_sigma)
        self.chaingroup_e.V = pe.Vr + rand(len(self.chaingroup)) * (pe.Vt - pe.Vr)
        self.chaingroup_i.V = pi.Vr + rand(len(self.chaingroup)) * (pi.Vt - pi.Vr)
        self.params = p

    def run(self):
        Network.run(self, self.params.duration)
        #print "self.params.wi ",self.params.wi,"\n"
        
    def plot(self):
        raster_plot(ylabel="Layer", title="Synfire chain raster plot",
                   color=(1, 0, 0), markersize=3,
                   showgrouplines=False, spacebetweengroups=0.2, grouplinecol=(0.5, 0.5, 0.5),
                   *self.mon_E)
        show()
        raster_plot(ylabel="Layer", title="Synfire chain raster plot",
                   color=(0, 1, 0), markersize=3,
                   showgrouplines=False, spacebetweengroups=0.2, grouplinecol=(0.5, 0.5, 0.5),
                   *self.mon_I)
        show()           

def estimate_params(mon, time_est):
    # Quick and dirty algorithm for the moment, for a more decent algorithm
    # use leastsq algorithm from scipy.optimize.minpack to fit const+Gaussian
    # http://www.scipy.org/doc/api_docs/SciPy.optimize.minpack.html#leastsq
    i, times = zip(*mon.spikes)
    times = array(times)
    times = times[abs(times - time_est) < 15 * ms]
    if len(times) == 0:
        return (0, 0 * ms)
    better_time_est = times.mean()
    times = times[abs(times - time_est) < 5 * ms]
    if len(times) == 0:
        return (0, 0 * ms)
    return (len(times), times.std())

def single_sfc(params_e = None, params_i = None):
    if params_e == None and params_i == None:
        net = DefaultNetwork(default_params,default_params)
    else:
        net = DefaultNetwork(params_e, params_i)
    #params.wi = -700    
    net.reinit(params_e,params_i)    
    net.run()
    net.plot()
    show()
    
def state_space(grid, neuron_multiply, verbose=True):
    amin = 0
    amax = 100
    sigmamin = 0. * ms
    sigmamax = 4. * ms

    params = default_params()
    params.num_layers = 1
    params.neurons_per_layer = int(params.neurons_per_layer * neuron_multiply)

    net = DefaultNetwork(params)

    i = 0
    #...................
    #uncomment these 2 lines for TeX labels
    #import pylab
    #pylab.rc_params.update({'text.usetex': True})
    #...................
    if verbose:
        print "Completed:"
    start_time = time.time()
    figure()
    for ai in range(grid + 1):
        for sigmai in range(grid + 1): #
            a = int(amin + (ai * (amax - amin)) / grid)
            if a > amax: a = amax
            sigma = sigmamin + sigmai * (sigmamax - sigmamin) / grid
            params.initial_burst_a, params.initial_burst_sigma = a, sigma
            net.reinit(params)
            net.run()
            (newa, newsigma) = estimate_params(net.mon_E[-1], params.initial_burst_t)
            newa = float(newa) / float(neuron_multiply)
            col = (float(ai) / float(grid), float(sigmai) / float(grid), 0.5)
            plot([sigma / ms, newsigma / ms], [a, newa], color=[0,0,0])
            plot([sigma / ms], [a], marker='.', color=[0,0,0], markersize=15)
            i += 1
            if verbose:
                print str(int(100. * float(i) / float((grid + 1) ** 2))) + "%",
        if verbose:
            print
    if verbose:
        print "Evaluation time:", time.time() - start_time, "seconds"
    xlabel('sigma (ms)')
    ylabel('a')
    title('Synfire chain state space')
    axis([sigmamin / ms, sigmamax / ms, 0, 120])

def probability_vs_a(neuron_multiply = 1, verbose=True):
    '''Generates figure 2C'''
    amin = 0
    amax = 100
    sigmamin = 0
    sigmamax = 5
    
    npts = 50
    step = 100/int(npts)
    
    params = default_params()
    params.num_layers = 1
    params.neurons_per_layer = params.neurons_per_layer * neuron_multiply

    net = DefaultNetwork(params)
    if verbose:
        print "Spike probability is being calculated for input volleys of varying neuronal number and dipersion:"
    start_time = time.time()
    figure()
    for sigmai in range(sigmamax+1):
        alpha = []
        for ai in xrange(0,amax + step,step): #
            params.initial_burst_a, params.initial_burst_sigma = ai, sigmai * ms
            net.reinit(params)
            net.run()
            (newa, newsigma) = estimate_params(net.mon[-1], params.initial_burst_t)
            newa = float(newa) / float(neuron_multiply)
            alpha.append(newa/float(amax))
        plot(xrange(0,amax + step,step),alpha)
    if verbose:
        print "Evaluation time:", time.time() - start_time, "seconds"
    xlabel('a (neurons)')
    ylabel('alpha (probability)')
    title('spike probability vs input spike number and sigma')
    axis([amin,amax,0,1])

def newsigma_vs_sigmain(neuron_multiply = 1, verbose=True):
    '''Generates figure 2d'''
    amin = 0
    amax = 100
    sigmamin = 0
    sigmamax = 5
    
    npts = 5
    
    params = default_params()
    params.num_layers = 1
    params.neurons_per_layer = params.neurons_per_layer * neuron_multiply

    net = DefaultNetwork(params)
    if verbose:
        print "\nSynchrony is being calculated for input volleys of varying neuronal number and dipersion:"
    start_time = time.time()
    figure()
    for ai in [45,65,100]:
        sigmaOut = []
        for sigmai in linspace(sigmamin,sigmamax,npts): #
            params.initial_burst_a, params.initial_burst_sigma = ai, sigmai * ms
            net.reinit(params)
            net.run()
            (newa, newsigma) = estimate_params(net.mon_E[-1], params.initial_burst_t)
            sigmaOut.append(newsigma)
        plot(linspace(sigmamin,sigmamax,npts),sigmaOut)
    if verbose:
        print "Evaluation time:", time.time() - start_time, "seconds"
    xlabel('sigma in (in ms)')
    ylabel('sigma out (in s)')
    title('synchrony vs input spike number and sigma')
    axis([sigmamin,sigmamax,sigmamin * ms,sigmamax * ms])

def aout_vs_ain(neuron_multiply = 1, verbose=True):
    '''Generates figure 4a'''
    amin = 0
    amax = 100
    sigmamin = 0
    sigmamax = 5
    
    npts = 10
    step = 100/int(npts)
    
    params = default_params()
    params.num_layers = 1
    params.neurons_per_layer = params.neurons_per_layer * neuron_multiply

    net = DefaultNetwork(params)
    if verbose:
        print "Final spike number is being calculated for input volleys of varying neuronal number and dipersion:"
    start_time = time.time()
    figure()
    for sigmai in range(sigmamax+1):
        aout = []
        for ai in xrange(0,amax + step,step): #
            params.initial_burst_a, params.initial_burst_sigma = ai, sigmai * ms
            net.reinit(params)
            net.run()
            (newa, newsigma) = estimate_params(net.mon_E[-1], params.initial_burst_t)
            newa = float(newa) / float(neuron_multiply)
            aout.append(newa)
        plot(xrange(0,amax + step,step),aout)
    if verbose:
        print "Evaluation time:", time.time() - start_time, "seconds"
    xlabel('a_in (spikes)')
    ylabel('a_out (spikes)')
    title('a_out vs input spike number a_in and sigma')
    axis([amin,amax,amin,amax])

def isoclines(grid, neuron_multiply, verbose=True):
    amin = 0
    amax = 100
    sigmamin = 0. * ms
    sigmamax = 4. * ms
    dsigma = 1. * ms
    params = default_params()
    params.num_layers = 1
    params.neurons_per_layer = int(params.neurons_per_layer * neuron_multiply)
    net = DefaultNetwork(params)
    i = 0
    
    if verbose:
        print "Completed:"
    start_time = time.time()
    figure()
    
    aouta = []
    aouts = []
    souta = []
    souts = []
    ovrlp = {}
    
    newsigma = 0. * ms
    for ai in range(grid + 1):
        ovrlp_s = []
        for sigmai in range(grid + 1):
            a = int(amin + (ai * (amax - amin)) / grid)
            if a > amax: a = amax
            sigma = sigmamin + sigmai * (sigmamax - sigmamin) / grid
            params.initial_burst_a, params.initial_burst_sigma = a, sigma
            net.reinit(params)
            net.run()
            (newa, newsigma) = estimate_params(net.mon_E[-1], params.initial_burst_t)
            newa = float(newa) / float(neuron_multiply)
       
            #col = (float(ai) / float(grid), float(sigmai) / float(grid), 0.5)
            plot([sigma / ms, newsigma / ms], [a, newa], color=[0,0,0])
            plot([sigma / ms], [a], marker='.', color=[0,0,0], markersize=15)
            if (newa-a >= 0): 
                aouta.append(a)
                aouts.append(sigma / ms)  
                plot([sigma / ms], [a], marker='.', color='b', markersize=15) 
            if (float(newsigma) - float(sigma)) < 0.00001: #float type conversion to avoid mismatch error
                souta.append(a)
                souts.append(sigma / ms)
                plot([sigma / ms], [a], marker='.', color='r', markersize=15) 
            if (newa-a >= 0) and (float(newsigma) - float(sigma)) < 0.00001: #float type used
                if a > 10:
                    ovrlp_s.append(sigma / ms)
                    ovrlp.update({a:ovrlp_s})
                plot([sigma / ms], [a], marker='.', color='g', markersize=15)                        
            i += 1
            if verbose:
                print str(int(100. * float(i) / float((grid + 1) ** 2))) + "%",
        if verbose:
            print
                    

    if verbose:
        print "Evaluation time:", time.time() - start_time, "seconds"

    print "\nThe points of intersection are:\n"

    xlabel('sigma (ms)')
    ylabel('a')
    title('Isoclines')
    axis([sigmamin / ms, sigmamax / ms, 0, 100])       

    print "stable fixed point at ",max(ovrlp.keys()),ovrlp[max(ovrlp.keys())][0]
    print "\nSaddle node at ",min(ovrlp.keys()),ovrlp[min(ovrlp.keys())][-1]
    print "\n"

def propTrace(neuron_multiply, weight, taum, verbose=True):
    amin = 0
    amax = 150
    sigmamin = 0. * ms
    sigmamax = 4. * ms
    dsigma = 1. * ms
    params = default_params()
    params.num_layers = 10
    params.neuron_multiply = 1
    #params.wi = weight
    #params.noise_inh_rate = weight
    #params.noise_inh = weight
    #params.noise_exc = 1-weight
    params.pr = weight
    params.taum = taum
    
    net = DefaultNetwork(params)
    delay = 0.7 * ms
    lsigma = {}
    
    avga = np.zeros(params.num_layers+1)
    avgs = np.zeros(params.num_layers+1)
    
    datpts = {40:sigmamin,60:sigmamin,100:3.0 * ms,65:sigmamax,90:sigmamax,98:sigmamin,41:sigmamax}
    if verbose:
        start = time.time()
        print "\nstart at {0} second".format(start) 
    for i in datpts.keys():
        params.initial_burst_a, params.initial_burst_sigma = i, datpts[i]
        net.reinit(params)
        
        avga = np.zeros(params.num_layers+1)
        avgs = np.zeros(params.num_layers+1)
        for j in range(neuron_multiply):
            net.run()
            newa = []
            newsigma = []
            newa.append(i)
            newsigma.append(float(datpts[i]))
            for k in range(params.num_layers):
                (a_, sigma_) = estimate_params(net.mon_E[k+1], params.initial_burst_t + k*delay)
                newa.append(a_)
                newsigma.append(float(sigma_))
            newa = array(newa)
            newsigma = array(newsigma)
            avga = avga + newa
            avgs = avgs + newsigma
        avga = avga/neuron_multiply
        print i,datpts[i],"\naverage a:",avga,"\n"
        avgs = (avgs/neuron_multiply)*1000 #seconds to msec conversion
        print i,datpts[i],"\naverage sigma:",avgs,"\n"
        plot([datpts[i] / ms], [i], marker='*', color='k', markersize=18)
        plot(avgs,avga,linestyle = '-')
    if verbose:
        print "\nend at {0} second\n".format(time.time())
        print "\nTime elapsed {0} seconds:".format(time.time() - start)  
                        
def fp_vs_inh(grid, neuron_multiply, weight, taum, verbose=True):
    print "\n---------------------\n"
    print "Running simulation...\n"
    
    amin = 0
    amax = 150
    sigmamin = 0. * ms
    sigmamax = 4. * ms
    dsigma = 1. * ms
    params = default_params()
    params.num_layers = 2
    params.neuron_multiply = neuron_multiply
    #params.wi = weight
    #params.noise_inh_rate = weight
    #params.noise_inh = weight
    #params.noise_exc = 1-weight
    params.pr = weight
    params.taum = taum * ms
    
    if params.num_layers > 1:
        params.total_neurons = params.neurons_per_layer * (params.num_layers-1)
    else:
        params.total_neurons = params.neurons_per_layer
    #print params.total_neurons,"\n"
    if neuron_multiply == 1:
        params.total_neurons = params.total_neurons + (params.neurons_per_layer*params.neuron_multiply)
    else: 
        params.total_neurons = params.total_neurons + (params.neurons_per_layer*params.neuron_multiply)
    #print params.total_neurons,"\n"    
    net = DefaultNetwork(params)
    
    #Single_sfc (without 5 ms delay)
    #single_sfc(params)
    
    #Verbose
    i = 0
    
    if verbose:
        print "Completed:"
    start_time = time.time()
    figure()
    
    lista_a = []
    lista_s = []
    lists_a = []
    lists_s = []
    ovrlp = {}
    bound_a = {}
    bound_sigma = {}
    newsigma = 0. * ms
    
    for ai in range(grid + 1):
        ovrlp_s = []
        bas = []
        bsa = []
        for sigmai in range(grid + 1):
            a = int(amin + (ai * (amax - amin)) / grid)
            if a > amax: a = amax
            sigma = sigmamin + sigmai * (sigmamax - sigmamin) / grid
            params.initial_burst_a, params.initial_burst_sigma = a, sigma
            #params.wi = weight
            #params.noise_inh_rate = weight
            net.reinit(params)
            #single_sfc(params)
            net.run()
            
            # Debug
            #show()
            #raster_plot(showgrouplines = True,*net.mon_E)
            #show()
            
            (newa, newsigma) = estimate_params(net.mon_E[-1], params.initial_burst_t)
            newa = float(newa) / float(params.neuron_multiply)
       
            #col = (float(ai) / float(grid), float(sigmai) / float(grid), 0.5)
            #plot([sigma / ms, newsigma / ms], [a, newa], color=[0,0,0])
            plot([sigma / ms], [a], marker='.', color=[0,0,0], markersize=15)
            if (newa-a >= 0): 
                if a > 10:
                    bas.append(sigma)
                    bound_a.update({a:bas})  
                plot([sigma / ms], [a], marker='.', color='b', markersize=15)
            try:     
                if (float(newsigma) - float(sigma)) < 0.00001:
                    if a > 30:
                        bsa.append(sigma)
                        bound_sigma.update({a:bsa})  
                    plot([sigma / ms], [a], marker='.', color='r', markersize=15)
            except fundamentalunits.DimensionMismatchError:
                 plot([sigma / ms], [a], marker='.', color='b', markersize=15)
            try:
                if (newa-a >= 0) and (float(newsigma) - float(sigma)) < 0.00001:
                    if a > 10:
                        ovrlp_s.append(newsigma*1000)
                        ovrlp.update({newa:ovrlp_s})
                    plot([sigma / ms], [a], marker='.', color='g', markersize=15)
            except fundamentalunits.DimensionMismatchError:
                plot([sigma / ms], [a], marker='.', color='b', markersize=15)              
            i += 1
            if verbose:
                print str(int(100. * float(i) / float((grid + 1) ** 2))) + "%",
        if verbose:
            print
    
   
    #plot(souts,souta,'r-')
    if verbose:
        print "Evaluation time:", time.time() - start_time, "seconds"

    '''
    foo = 1
    while(foo):
        if min(ovrlp.keys()) < 10:
            try:
                del ovrlp[min(ovrlp.keys())]
            except KeyError:
                foo = 0
    '''
    
    #...................
    #uncomment these 2 lines for TeX labels
    #import pylab
    #pylab.rc_params.update({'text.usetex': True})
    #...................
    
    # Plot propagation trace for few grid points)
    propTrace(neuron_multiply, weight, params.taum)
    
    # Pick up the boundary points
    for i in bound_a.keys():
        lista_a.append(i)
        lista_s.append(max(bound_a[i]))
    for i in bound_sigma.keys():
        lists_a.append(i)
        lists_s.append(min(bound_sigma[i]))
    
    z_a = np.polyfit(lista_a,lista_s,2)
    pol_a = np.poly1d(z_a)
    print "pol_a : ",z_a,"\n"
    z_s = np.polyfit(lists_a,lists_s,2)
    print "pol_s : ",z_s,"\n"    
    pol_s = np.poly1d(z_s)
    tmpa = linspace(amin,amax+100,50)
    plot(pol_a(tmpa) / ms,tmpa,'b-.',label = "a-nullcline")
    plot(pol_s(tmpa) / ms,tmpa,'r-.',label = "sigma-nullcline")
    mpl.rcParams['legend.fontsize'] = 10
    xlabel('sigma (ms)')
    ylabel('a')
    title('Isoclines')
    legend()
    axis([sigmamin / ms, sigmamax / ms, amin, amax])     
    savefig(("wi_{0}_{2}_{1}_{3}.png").format(params.wi,params.neuron_multiply,weight,taum), bbox_inches='tight')
    close()
 
    figure()                               
    plot(pol_a(tmpa) / ms,tmpa,'b-',label = "a : y = {0} + {1}x + {2}x^2".format(z_a[0],z_a[1],z_a[2]))
    plot(pol_s(tmpa) / ms,tmpa,'r-',label = "sigma :y = {0} + {1}x + {2}x^2".format(z_s[0],z_s[1],z_s[2]))
    mpl.rcParams['legend.fontsize'] = 7   
    xlabel('sigma (ms)')
    ylabel('a')
    title('Isoclines')
    legend()
    axis([sigmamin / ms, sigmamax / ms, 0, 200])    
    savefig(("isoclines_{0}_{2}_{1}_{3}.png").format(params.wi,params.neuron_multiply,weight,taum), bbox_inches='tight')
    close()
    
    print "\nThe points of intersection are:\n"     
    print "\nweight ",weight  
     
    if ovrlp.keys()!=[]:
        print "\nstable fixed point at ",max(ovrlp.keys()),ovrlp[max(ovrlp.keys())][0]
        print "\nSaddle node at ",min(ovrlp.keys()),ovrlp[min(ovrlp.keys())][-1]
        print "\n"       
        return array([(max(ovrlp.keys()),ovrlp[max(ovrlp.keys())][0]),(min(ovrlp.keys()),ovrlp[min(ovrlp.keys())][-1])])

    else:
        print "None\n"
        return ((0,0),(0,0))

def fpVsInhRun():
    params = default_params()
    wi = params.wi #changes intragroup inhibition
    taum = params.taum
    noise_inh_rate = params.noise_inh_rate
    sfp = [] #Stable fixed point list
    sn = []  #Saddle node list
    ratio = []
    for i in linspace(10,20,10):
        temp = fp_vs_inh(15,50,1,i,True)
        sfp.append(temp[0])
        sn.append(temp[1])
        ratio.append(i)

    sfp = array(sfp)
    sn = array(sn)
    ratio = array(ratio)

    z = ratio
    xst = sfp[:,0]
    yst = sfp[:,1]
    xsn = sn[:,0]
    ysn = sn[:,1] 

    # Save the data
    f_sfp = open("sfp.p","wb")
    f_sn  = open("sn.p","wb")
    f_z = open("z.p","wb")
    pickle.dump(sfp, f_sfp) 
    pickle.dump(sn, f_sn)
    pickle.dump(z, f_z)
    
def loadPlotData():
    sfp = [] #Stable fixed point list
    sn = []  #Saddle node list
    
    sfp = pickle.load(open("sfp.p",'r'))
    sn = pickle.load(open("sn.p",'r'))
    z = pickle.load(open("z.p",'r'))

    xst = sfp[:,0]
    yst = sfp[:,1]
    xsn = sn[:,0]
    ysn = sn[:,1] 

    # Plot in 3D
    mpl.rcParams['legend.fontsize'] = 10
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    ax.plot(xst, yst, z, label='stable fixed points')
    ax.plot(xsn, ysn, z, label='saddle node points')
    ax.legend()
    plt.show()

    
##--------------------------------------------
## Uncomment below functions to generate state space
##--------------------------------------------
#print 'Computing SFC with multiple layers'
#print 'Plotting SFC state space'
#state_space(10,1)
#state_space(8,10)
#state_space(10,100)
#state_space(10,50)
#isoclines(10,50)

##--------------------------------------------
## Uncomment below function to run and plot fixed point vs inhibition
##--------------------------------------------
#fpVsInhRun()
#loadPlotData()
#propTrace(100,-90)

params = default_params()
params.initial_burst_a, params.initial_burst_sigma = 54, 0 * ms
single_sfc(params)

show()
##--------------------------------------------
## Uncomment below functions to generate figures 2c,2d,3a,4a,4b,4c/3c and 4d
##--------------------------------------------
#probability_vs_a(1)
#newsigma_vs_sigmain(1)
#aout_vs_ain(1)
#show()
