
Mode = Df.Key("mode", str)
RecoverAttempts = Df.Key("recoverAttempts", int)
TargetLost = Df.Key("targetLost", bool)
ForceRecover = Df.Key("forceRecover", bool)
Lane = Df.Key("lane", str)


def Root(ctx):
    if ctx.State.Get(Mode) is None:
        ctx.State.Set(Mode, "patrol")

    if ctx.State.Get(RecoverAttempts) is None:
        ctx.State.Set(RecoverAttempts, 0)

    yield Df.Act("RootStart", {"mode": ctx.State.Get(Mode)})
    yield from PatrolBeat(ctx)

    if bool(ctx.State.Get(TargetLost, False)):
        yield Df.Push("RecoverBeat")

    yield Df.Act("RootDone", {"mode": ctx.State.Get(Mode)})
    yield Df.Succeed()


def PatrolBeat(ctx):
    yield Df.Act("PatrolLook")
    yield Df.Wait(1)
    yield Df.Act("PatrolStep", {"lane": ctx.State.Get(Lane, "north")})

    if bool(ctx.State.Get(ForceRecover, False)):
        ctx.State.Set(TargetLost, True)
        yield Df.Act("TargetLost")
    else:
        ctx.State.Set(TargetLost, False)
        yield Df.Act("TargetVisible")


def RecoverBeat(ctx):
    recoverAttempts = ctx.State.Get(RecoverAttempts, 0) + 1
    ctx.State.Set(RecoverAttempts, recoverAttempts)

    yield Df.Act("RecoverSweep", {"attempt": recoverAttempts})
    yield Df.Wait(2)

    if recoverAttempts >= 2:
        ctx.State.Set(Mode, "fallback")
        yield Df.Act("RecoverFallback")
    else:
        ctx.State.Set(Mode, "patrol")
        yield Df.Act("RecoverLock")

    yield Df.Pop({"recoverAttempts": recoverAttempts})
