Choice = Df.Key("storyChoice", str)


def Root(ctx):
    yield Story.Line("The barrow breathed smoke.")
    yield Story.Say("Wiglaf", "I will stand with you.")
    yield from Story.Choice(
        "What do you do?",
        (
            Story.Option("stand", "Stand your ground"),
            Story.Option("call", "Call to your men"),
        ),
        StoreAs=Choice,
        ctx=ctx,
    )

    if ctx.State.Get(Choice) == "stand":
        yield Story.Line("You raise your shield and hold the ridge.")
    else:
        yield Story.Line("Your horn-call cuts through the ash.")

    yield Df.Steady()
