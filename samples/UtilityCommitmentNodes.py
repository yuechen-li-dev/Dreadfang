
Signal = Df.Key("signal", float)
SignalSeries = Df.Key("signalSeries", tuple)
SignalIndex = Df.Key("signalIndex", int)
Hysteresis = Df.Key("hysteresis", float)
MinCommitTicks = Df.Key("minCommitTicks", int)


def TrackScore(ctx):
    signal = ctx.State.Get(Signal, 0.0)
    return signal


def RecoverScore(ctx):
    signal = ctx.State.Get(Signal, 0.0)
    return 1.0 - signal


def Root(ctx):
    ctx.State.Set(SignalIndex, 0)
    yield from StepSignals(ctx)
    yield Df.Succeed()


def StepSignals(ctx):
    signalSeries = ctx.State.Get(SignalSeries, ())
    signalIndex = ctx.State.Get(SignalIndex, 0)

    if signalIndex < len(signalSeries):
        signal = float(signalSeries[signalIndex])
        ctx.State.Set(Signal, signal)
        yield Df.Act("SignalObserved", {"signal": signal})
        yield Df.Decide(
            [
                Df.Option("Track", TrackScore, "TrackBeat"),
                Df.Option("Recover", RecoverScore, "RecoverBeat"),
            ],
            hysteresis=ctx.State.Get(Hysteresis, 0.0),
            min_commit_ticks=ctx.State.Get(MinCommitTicks, 0),
        )
        yield Df.Wait(1)
        ctx.State.Set(SignalIndex, signalIndex + 1)
        yield from StepSignals(ctx)


def TrackBeat(_ctx):
    yield Df.Act("TrackBeat")
    yield Df.Pop()


def RecoverBeat(_ctx):
    yield Df.Act("RecoverBeat")
    yield Df.Pop()
