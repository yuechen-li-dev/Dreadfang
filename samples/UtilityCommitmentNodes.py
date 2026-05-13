
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
    signalSeries = ctx.State.Get(SignalSeries, ())
    signalIndex = 0

    for sample in signalSeries:
        signal = float(sample)
        ctx.State.Set(Signal, signal)
        ctx.State.Set(SignalIndex, signalIndex)
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
        signalIndex = signalIndex + 1

    yield Df.Succeed()


def TrackBeat(_ctx):
    yield Df.Act("TrackBeat")
    yield Df.Pop()


def RecoverBeat(_ctx):
    yield Df.Act("RecoverBeat")
    yield Df.Pop()
