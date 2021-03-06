import numpy as np
import torch

# VECTORIZE
def lif_compute(I_total, R, tau_V, Th, dt,
                torched=False, grad=False, device="cpu"):
    if torched:
        return lif_compute_torched(I_total, R, tau_V, Th, dt, grad, device)
    else:
        return lif_compute_np(I_total, R, tau_V, Th, dt)

def lif_compute_np(I_total, R, tau_V, Th, dt):
    EL = -70.0  # mV
    V_th = Th  # -50
    V = np.ones((I_total.shape[1]))*EL

    V_reset = -90.0

    k = 0
    total_time = len(I_total) - 1.0/dt
    V_out = np.zeros(I_total.shape)

    spike_reset_count = np.zeros((I_total.shape[1],1))

    while k <= total_time:
        # LIF equation
        dq_dt = 1.0 / tau_V * (-1.0 * (V - EL) + R * I_total[k])
        V += dt*dq_dt

        # Spike
        spike = 50.0*np.greater_equal(V, V_th) # Spike
        spike_reset_add = ((int(1.0/dt)+1)*np.greater_equal(V, V_th))
        spike_reset_count = np.add(spike_reset_count, spike_reset_add[:,None])

        # No spike # Refractory period should be 1ms +- 0.5
        subthresh = np.multiply(np.equal(spike_reset_count, 0.0),V[:,None])
        reset = np.multiply(np.greater(spike_reset_count, 0.0),V_reset)
        reset_or_subthres = reset + subthresh
        no_spike = np.multiply(reset_or_subthres, np.less(V, V_th)[:,None]).flatten()

        V_out[k] = spike + no_spike
        V = np.multiply(V_out[k,:], np.equal(spike_reset_count, 0.0).flatten()) + reset.flatten()

        spike_reset_count = spike_reset_count - 1.0*np.greater(spike_reset_count, 0.0)

        k += 1

        # # Spike
        # if np.greater_equal(V, V_th): # V >= V_th:
        #     V_out[k] = 50.0  # TODO: ???
        #     V_out[k+1:int(k+1.0/dt)+1] = V_reset # TODO: ???
        #     0:10+1 -> 11 steps

        #     k += int(1.0/dt) # TODO: ???
        # # No spike
        # else:
        #     V_out[k] = V
        #     k += 1
        # V = V_out[k-1]
    
    while k < V_out.shape[0]:
        V_out[k] = V
        k += 1
    
    return V_out

def lif_compute_torched(I_total, R, tau_V, Th, dt,
                grad=False, device="cpu"):
    torch.autograd.set_grad_enabled(grad)

    EL = -70.0  # mV
    V_th = Th  # -50
    V = torch.ones(I_total.shape[1], device=device)*EL

    V_reset = -90.0

    k = 0
    total_time = len(I_total) - 1.0/dt
    V_out = torch.zeros(I_total.shape, device=device)

    spike_reset_count = torch.zeros(I_total.shape[1],1, device=device)

    while k <= total_time:
        # LIF equation
        dq_dt = -1.0 * (V - EL)
        add = float(R) * I_total[k].float()
        dq_dt = dq_dt + add
        dq_dt = 1.0 / tau_V * dq_dt
        V = V + dt*dq_dt

        # Spike
        spike = 50.0*torch.ge(V, V_th).float() # Spike
        spike_reset_add = ((int(1.0/dt)+1.0)*torch.ge(V, V_th))
        spike_reset_count = torch.add(spike_reset_count, spike_reset_add[:,None].float())

        # No spike
        subthresh = torch.mul(torch.eq(spike_reset_count, 0.0).float(), V[:,None].float())
        reset = torch.mul(torch.gt(spike_reset_count, 0.0).float(), V_reset)
        reset_or_subthres = reset + subthresh
        no_spike = torch.mul(reset_or_subthres, torch.lt(V, V_th)[:,None].float()).flatten()

        V_out[k] = spike + no_spike
        V = torch.mul(V_out[k,:], torch.eq(spike_reset_count, 0.0).float().flatten()) + reset.flatten()

        spike_reset_count = spike_reset_count - 1.0*torch.gt(spike_reset_count, 0.0).float()

        k += 1

        # # Spike
        # if np.greater_equal(V, V_th): # V >= V_th:
        #     V_out[k] = 50.0  # TODO: ???
        #     V_out[k+1:int(k+1.0/dt)+1] = V_reset # TODO: ???
        #     0:10+1 -> 11 steps

        #     k += int(1.0/dt) # TODO: ???
        # # No spike
        # else:
        #     V_out[k] = V
        #     k += 1
        # V = V_out[k-1]

    while k < V_out.shape[0]:
        V_out[k] = V
        k += 1

    return V_out

def spike_binary(V, torched=False, grad=False, device="cpu"):
    if torched:
        return spike_binary_torched(V, grad, device)
    else:
        return spike_binary_np(V)

def spike_binary_np(V: np.array):
    thres = -20 # mv
    trial_num = V.shape[1]
    F = np.zeros((V.shape[0]+1, V.shape[1]))
    TINY_VAL = -90.0 * np.ones((trial_num))

    # CONVERT SPIKE INTO DIRAC DELTA
    # Shift right a copy of V by 1; where copy intersects with V can be
    # used as a point representing the spike
    V_trial = np.concatenate((V, [TINY_VAL]))
    V_trial_shifted = np.concatenate(([TINY_VAL], V))

    spike_bool = np.logical_and(V_trial > thres, thres > V_trial_shifted)
    F = 1.0 * spike_bool
    
    return F[1:, :]

def spike_binary_torched(V: torch.tensor, grad=False, device="cpu"):
    torch.set_grad_enabled(grad)

    thres = -20 # mv
    trial_num = V.shape[1]
    TINY_VAL = -90.0 * torch.ones(1, trial_num, requires_grad=grad,
                                  device=device)

    # CONVERT SPIKE INTO DIRAC DELTA
    # Shift right a copy of V by 1; where copy intersects with V can be
    # used as a point representing the spike
    # V_trial = torch.cat((V, TINY_VAL))
    # V_trial_shifted = torch.cat((TINY_VAL, V))
    #
    # spike_bool = torch.mul(torch.gt(V_trial, thres), torch.le(V_trial_shifted, thres)).double()

    spike_bool = (torch.nn.functional.relu(V) / 50.0).double()

    # spike_bool = np.logical_and(V_trial > thres, thres > V_trial_shifted)
    # F = 1.0 * spike_bool
    # F.dtype = 
    # print(type(F[1:, :]))

    # return F[1:, :]
    return spike_bool

# TODO: VECTORIZE
def spike_binary_ghetto(V: np.array):
    thres = -20 # mv
    trial_num = V.shape[1]
    F = np.zeros((V.shape[0]+1, V.shape[1]))
    TINY_VAL = -90.0

    for i in range(0, trial_num):
        # CONVERT SPIKE INTO DIRAC DELTA
        # Shift right a copy of V by 1; where copy intersects with V can be
        # used as a point representing the spike
        V_trial = np.concatenate((V[:,i], [TINY_VAL]))
        V_trial_shifted = np.concatenate(([TINY_VAL], V[:,]))

        spike_bool = V_trial > thres > V_trial_shifted
        F[:, i] = 1.0 * spike_bool

    return F[2:, :]

def id_synaptic_waveform(dt, t_end, tau_rise, tau_fall,random_delay=False,delay_mean=0,delay_std=1):
    t = np.arange(0.0, t_end, dt)
    tp = tau_rise*tau_fall / (tau_fall-tau_rise) * np.log(tau_fall/tau_rise)
    factor = -np.exp(-tp/tau_rise) + np.exp(-tp/tau_fall)
    waveform = 1.0/factor * (np.exp(-t/tau_fall) - np.exp(-t/tau_rise))
    if random_delay:
        delay_samples = int((delay_std * np.random.randn() + delay_mean + 20)/dt)
        delayed_waveform = np.zeros(len(t))
        delayed_waveform[delay_samples:] = waveform[0:len(waveform)-delay_samples]
        return delayed_waveform
    else:
        delay_samples = int((delay_std * np.random.randn() + 20)/dt)
        delayed_waveform = np.zeros(len(t))
        delayed_waveform[delay_samples:] = waveform[0:len(waveform)-delay_samples]
        return delayed_waveform
    
def gaussian_kernel(dt, sig):
    t = np.arange(-(sig*3.0), sig*3.0, dt) # 3 standard deviations on either side
    gauss_kernel = 1.0/(sig*np.sqrt(2.0*np.pi))*np.exp(-1.0*np.power(t, 2.0)/(2.0*np.power(sig, 2.0)))
    gauss_kernel /= np.linalg.norm(gauss_kernel, ord=1)*dt # Want area under curve to be 1

    return gauss_kernel