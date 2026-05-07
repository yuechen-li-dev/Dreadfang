
def TrackScore(ctx):
    signal = float(ctx.State.Get("signal", 0.0))
    return signal


def RecoverScore(ctx):
    signal = float(ctx.State.Get("signal", 0.0))
    return 1.0 - signal


def Root(ctx):
    ctx.State.Set("signalIndex", 0)
    yield from StepSignals(ctx)
    yield Df.Succeed()


def StepSignals(ctx):
    signalSeries = ctx.State.Get("signalSeries", ())
    signalIndex = int(ctx.State.Get("signalIndex", 0))

    if signalIndex < len(signalSeries):
        signal = float(signalSeries[signalIndex])
        ctx.State.Set("signal", signal)
        yield Df.Act("SignalObserved", {"signal": signal})
        yield Df.Decide(
            [
                Df.Option("Track", TrackScore, "TrackBeat"),
                Df.Option("Recover", RecoverScore, "RecoverBeat"),
            ],
            hysteresis=float(ctx.State.Get("hysteresis", 0.0)),
            min_commit_ticks=int(ctx.State.Get("minCommitTicks", 0)),
        )
        yield Df.Wait(1)
        ctx.State.Set("signalIndex", signalIndex + 1)
        yield from StepSignals(ctx)


def TrackBeat(_ctx):
    yield Df.Act("TrackBeat")
    yield Df.Pop()


def RecoverBeat(_ctx):
    yield Df.Act("RecoverBeat")
    yield Df.Pop()
