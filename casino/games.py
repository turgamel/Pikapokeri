# Standard Library
import asyncio
import random

# Casino
from .deck import Deck
from .engine import game_engine

# Red
from redbot.core import bank
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.predicates import MessagePredicate

# Discord
import discord

vs = [(':diamonds:', 10), (':diamonds:', "Jack"), (':diamonds:', "Queen"), (':diamonds:', "King"), (':diamonds:', "Ace")]
_ = Translator("Casino", __file__)
deck = Deck()

# Any game created must return a tuple of 3 arguments.
# The outcome (True or False)
# The final bet or amount (int)
# A msg that is either a string or an embed
# If the msg is a string it is added to the description of the final embed.
# If the msg is an embed, it's fields are added to the final embed.


class Core:
    """
    A simple class to hold the basic original Casino mini games.

    Games
    -----------
    Allin
        Bet all your credits. All or nothing gamble.
    Coin
        Coin flip game. Pick heads or tails.
    Cups
        Three cups are shuffled. Pick the one covering the ball.
    Dice
        Roll a pair of die. 2, 7, 11, or 12 wins.
    Hilo
        Guess if the dice result will be high, low, or 7.
    Craps
        Win with a comeout roll of 7 or 11, lose on 2, 3, or 12.
        If you roll any other number you must match it on your
        second roll to win.
    Pikapokeri
        You know.
    """

    @game_engine("Allin")
    async def play_allin(self, ctx, bet, multiplier):
        await ctx.send(
            _("You put all your chips into the machine and pull the lever...")
        )
        await asyncio.sleep(3)
        outcome = random.randint(0, multiplier + 1)
        if outcome == 0:
            msg = "▂▃▅▇█▓▒░ [♠]  [♥]  [♦]  [♣] ░▒▓█▇▅▃▂\n"
            msg += _("          CONGRATULATIONS YOU WON\n")
            msg += _("░▒▓█▇▅▃▂ ⚅ J A C K P O T ⚅ ▂▃▅▇█▓▒░")
            msg = box(msg, lang="py")
            bet *= multiplier
        else:
            msg = _(
                "Nothing happens. You stare at the machine contemplating your decision."
            )
        return outcome == 0, bet, msg

    @game_engine("Coin", (_("heads"), _("tails")))
    async def play_coin(self, ctx, bet, choice):
        await ctx.send(_("The coin flips into the air..."))
        await asyncio.sleep(2)
        outcome = random.choice((_("heads"), _("tails")))
        msg = _("The coin landed on {}!").format(outcome)
        return choice.lower() in outcome, bet, msg

    @game_engine("Cups", ("1", "2", "3"))
    async def play_cups(self, ctx, bet, choice):
        await ctx.send(_("The cups start shuffling along the table..."))
        await asyncio.sleep(3)
        outcome = random.randint(1, 3)
        msg = _("The coin was under cup {}!").format(outcome)
        return int(choice) == outcome, bet, msg

    @game_engine("Dice")
    async def play_dice(self, ctx, bet):
        await ctx.send(
            _(
                "The dice strike the back of the table and begin to tumble into "
                "place..."
            )
        )
        await asyncio.sleep(2)
        die_one, die_two = self.roll_dice()
        outcome = die_one + die_two

        msg = _("The dice landed on {} and {} ({}).").format(die_one, die_two, outcome)
        return outcome in (2, 7, 11, 12), bet, msg

    @game_engine("Hilo", (_("low"), _("lo"), _("high"), _("hi"), _("seven"), _("7")))
    async def play_hilo(self, ctx, bet, choice):
        await ctx.send(_("The dice hit the table and slowly fall into place..."))
        await asyncio.sleep(2)

        result = sum(self.roll_dice())
        if result < 7:
            outcome = (_("low"), _("lo"))
        elif result > 7:
            outcome = (_("high"), _("hi"))
        else:
            outcome = (_("seven"), "7")

        msg = _("The outcome was {} ({[0]})!").format(result, outcome)

        if result == 7 and outcome[1] == "7":
            bet *= 5

        return choice.lower() in outcome, bet, msg

    @game_engine(name="Craps")
    async def play_craps(self, ctx, bet):
        return await self._craps_game(ctx, bet)

    async def _craps_game(self, ctx, bet, comeout=False):
        await ctx.send(_("The dice strike against the back of the table..."))
        await asyncio.sleep(2)
        d1, d2 = self.roll_dice()
        result = d1 + d2
        msg = _("You rolled a {} and {}.")

        if comeout:
            if result == comeout:
                return True, bet, msg.format(d1, d2)
            return False, bet, msg.format(d1, d2)

        if result == 7:
            bet *= 3
            return True, bet, msg.format(d1, d2)
        elif result == 11:
            return True, bet, msg.format(d1, d2)
        elif result in (2, 3, 12):
            return False, bet, msg.format(d1, d2)

        await ctx.send(
            "{}\nI'll roll the dice one more time. This time you will need exactly "
            "{} to win.".format(msg.format(d1, d2), d1 + d2)
        )
        return await self._craps_game(ctx, bet, comeout=result)

    @staticmethod
    def roll_dice():
        return random.randint(1, 6), random.randint(1, 6)


class Blackjack:
    """A simple class to hold the game logic for Blackjack.

    Blackjack requires inheritance from data to verify the user
    can double down.
    """

    def __init__(self):
        super().__init__()

    @game_engine(name="Blackjack")
    async def play(self, ctx, bet):
        ph, dh, amt = await self.blackjack_game(ctx, bet)
        result = await self.blackjack_results(ctx, amt, ph, dh)
        return result

    @game_engine(name="Blackjack")
    async def mock(self, ctx, bet, ph, dh):
        result = await self.blackjack_results(ctx, bet, ph, dh)
        return result

    async def blackjack_game(self, ctx, amount):
        ph = deck.deal(num=2)
        ph_count = deck.bj_count(ph)
        dh = deck.deal(num=2)

        # End game if player has 21
        if ph_count == 21:
            return ph, dh, amount
        options = (_("hit"), _("stay"), _("double"))
        condition1 = MessagePredicate.lower_contained_in(options, ctx=ctx)
        condition2 = MessagePredicate.lower_contained_in((_("hit"), _("stay")), ctx=ctx)

        embed = self.bj_embed(ctx, ph, dh, ph_count, initial=True)
        await ctx.send(ctx.author.mention, embed=embed)

        try:
            choice = await ctx.bot.wait_for("message", check=condition1, timeout=35.0)
        except asyncio.TimeoutError:
            dh = self.dealer(dh)
            return ph, dh, amount

        if choice.content.lower() == _("stay"):
            dh = self.dealer(dh)
            return ph, dh, amount

        if choice.content.lower() == _("double"):
            return await self.double_down(ctx, ph, dh, amount, condition2)
        else:
            ph, dh = await self.bj_loop(ctx, ph, dh, ph_count, condition2)
            dh = self.dealer(dh)
            return ph, dh, amount

    async def double_down(self, ctx, ph, dh, amount, condition2):
        try:
            await bank.withdraw_credits(ctx.author, amount)
        except ValueError:
            await ctx.send(
                _("{} You can not cover the bet. Please choose " "hit or stay.").format(
                    ctx.author.mention
                )
            )

            try:
                choice2 = await ctx.bot.wait_for(
                    "message", check=condition2, timeout=35.0
                )
            except asyncio.TimeoutError:
                return ph, dh, amount

            if choice2.content.lower() == _("stay"):
                dh = self.dealer(dh)
                return ph, dh, amount
            elif choice2.content.lower() == _("hit"):
                ph, dh = await self.bj_loop(ctx, ph, dh, deck.bj_count(ph), condition2)
                dh = self.dealer(dh)
                return ph, dh, amount
        else:
            deck.deal(hand=ph)
            dh = self.dealer(dh)
            amount *= 2
            return ph, dh, amount

    async def blackjack_results(self, ctx, amount, ph, dh):
        dc = deck.bj_count(dh)
        pc = deck.bj_count(ph)

        if dc > 21 >= pc or dc < pc <= 21:
            outcome = _("Winner!")
            result = True
        elif pc > 21:
            outcome = _("BUST!")
            result = False
        elif dc == pc <= 21:
            outcome = _("Pushed")
            await bank.deposit_credits(ctx.author, amount)
            result = False
        else:
            outcome = _("House Wins!")
            result = False
        embed = self.bj_embed(ctx, ph, dh, pc, outcome=outcome)
        return result, amount, embed

    async def bj_loop(self, ctx, ph, dh, count, condition2):
        while count < 21:
            ph = deck.deal(hand=ph)
            count = deck.bj_count(hand=ph)

            if count >= 21:
                break
            embed = self.bj_embed(ctx, ph, dh, count)
            await ctx.send(ctx.author.mention, embed=embed)
            try:
                resp = await ctx.bot.wait_for("message", check=condition2, timeout=35.0)
            except asyncio.TimeoutError:
                break

            if resp.content.lower() == _("stay"):
                break
            else:
                continue

        # Return player hand & dealer hand when count >= 21 or the player picks stay.
        return ph, dh

    @staticmethod
    def dealer(dh):
        count = deck.bj_count(dh)
        # forces hit if ace in first two cards without 21
        if deck.hand_check(dh, "Ace") and count != 21:
            deck.deal(hand=dh)
            count = deck.bj_count(dh)

        # defines maximum hit score X
        while count < 16:
            deck.deal(hand=dh)
            count = deck.bj_count(dh)
        return dh

    @staticmethod
    def bj_embed(ctx, ph, dh, count1, initial=False, outcome=None):
        hand = _("{}\n**Score:** {}")
        footer = _("Cards in Deck: {}")
        start = _("**Options:** hit, stay, or double")
        after = _("**Options:** hit or stay")
        options = "**Outcome:** " + outcome if outcome else start if initial else after
        count2 = deck.bj_count(dh, hole=True) if not outcome else deck.bj_count(dh)
        hole = " ".join(deck.fmt_hand([dh[0]]))
        dealer_hand = hole if not outcome else ", ".join(deck.fmt_hand(dh))

        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(
            name=_("{}'s Hand").format(ctx.author.name),
            value=hand.format(", ".join(deck.fmt_hand(ph)), count1),
        )
        embed.add_field(
            name=_("{}'s Hand").format(ctx.bot.user.name),
            value=hand.format(dealer_hand, count2),
        )
        embed.add_field(name="\u200b", value=options, inline=False)
        embed.set_footer(text=footer.format(len(deck)))
        return embed


class War:
    """A simple class for the war card game."""

    @game_engine("War")
    async def play(self, ctx, bet):
        outcome, player_card, dealer_card, amount = await self.war_game(ctx, bet)
        return await self.war_results(outcome, player_card, dealer_card, amount)

    async def war_game(self, ctx, bet):
        player_card, dealer_card, pc, dc = self.war_draw()

        await ctx.send(
            _(
                "The dealer shuffles the deck and deals 2 cards face down. One for the "
                "player and one for the dealer..."
            )
        )
        await asyncio.sleep(2)
        await ctx.send(_("**FLIP!**"))
        await asyncio.sleep(1)

        if pc != dc:
            if pc >= dc:
                outcome = "Win"
            else:
                outcome = "Loss"
            return outcome, player_card, dealer_card, bet

        await ctx.send(
            _(
                "The player and dealer are both showing a **{}**!\nTHIS MEANS "
                "WAR! You may choose to surrender and forfeit half your bet, or "
                "you can go to war.\nIf you go to war your bet will be doubled, "
                "but the multiplier is only applied to your original bet, the rest will "
                "be pushed."
            ).format(deck.fmt_card(player_card))
        )
        pred = MessagePredicate.lower_contained_in(
            (_("war"), _("surrender"), _("ffs")), ctx=ctx
        )
        try:
            choice = await ctx.bot.wait_for("message", check=pred, timeout=35.0)
        except asyncio.TimeoutError:
            return "Surrender", player_card, dealer_card, bet

        if choice is None or choice.content.title() in (_("Surrender"), _("Ffs")):
            outcome = "Surrender"
            bet /= 2
            return outcome, player_card, dealer_card, bet
        else:
            player_card, dealer_card, pc, dc = self.burn_and_draw()

            await ctx.send(
                _("The dealer burns three cards and deals two cards face down...")
            )
            await asyncio.sleep(3)
            await ctx.send(_("**FLIP!**"))

            if pc >= dc:
                outcome = "Win"
            else:
                outcome = "Loss"
            return outcome, player_card, dealer_card, bet

    @staticmethod
    async def war_results(outcome, player_card, dealer_card, amount):
        msg = _("**Player Card:** {}\n**Dealer Card:** {}\n" "").format(
            deck.fmt_card(player_card), deck.fmt_card(dealer_card)
        )
        if outcome == "Win":
            msg += _("**Result**: Winner")
            return True, amount, msg

        elif outcome == "Loss":
            msg += _("**Result**: Loser")
            return False, amount, msg
        else:
            msg += _("**Result**: Surrendered")
            return False, amount, msg

    @staticmethod
    def get_count(pc, dc):
        return deck.war_count(pc), deck.war_count(dc)

    def war_draw(self):
        player_card, dealer_card = deck.deal(num=2)
        pc, dc = self.get_count(player_card, dealer_card)
        return player_card, dealer_card, pc, dc

    def burn_and_draw(self):
        deck.burn(3)
        player_card, dealer_card = deck.deal(num=2)
        pc, dc = self.get_count(player_card, dealer_card)
        return player_card, dealer_card, pc, dc


class Double:
    """A simple class for the Double Or Nothing game."""

    @game_engine("Double")
    async def play(self, ctx, bet):
        count, amount = await self.double_game(ctx, bet)
        return await self.double_results(ctx, count, amount)

    async def double_game(self, ctx, bet):
        count = 0

        while bet > 0:
            count += 1

            flip = random.randint(0, 1)

            if flip == 0:
                bet = 0
                break
            else:
                bet *= 2

            pred = MessagePredicate.lower_contained_in(
                (_("double"), _("cash out")), ctx=ctx
            )

            embed = self.double_embed(ctx, count, bet)
            await ctx.send(ctx.author.mention, embed=embed)
            try:
                resp = await ctx.bot.wait_for("message", check=pred, timeout=35.0)
            except asyncio.TimeoutError:
                break

            if resp.content.lower() == _("cash out"):
                break
            else:
                continue

        return count, bet

    async def double_results(self, ctx, count, amount):
        if amount > 0:
            outcome = _("Cashed Out!")
            result = True
        else:
            outcome = _("You Lost It All!")
            result = False
        embed = self.double_embed(ctx, count, amount, outcome=outcome)
        return result, amount, embed

    @staticmethod
    def double_embed(ctx, count, amount, outcome=None):
        double = _("{}\n**DOUBLE!:** x{}")
        zero = _("{}\n**NOTHING!**")
        choice = _("**Options:** double or cash out")
        options = "**Outcome:** " + outcome if outcome else choice

        if amount == 0:
            score = zero.format(amount)
        else:
            score = double.format(amount, count)

        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(name=_("{}'s Score").format(ctx.author.name), value=score)
        embed.add_field(name="\u200b", value=options, inline=False)
        if not outcome:
            embed.add_field(
                name="\u200b",
                value="Remember, you can cash out at anytime.",
                inline=False,
            )
        embed.set_footer(text="Try again and test your luck!")
        return embed


class Pikapokeri:
    """Pikapokeri"""

    def __init__(self):
        super().__init__()

    @game_engine("Pikapokeri")
    async def play(self, ctx, bet):
        amount, win, ph, msg = await self.play_pikapokeri(ctx, bet)
        if amount > bet:
            count, amount, win = await self.tuplaa(ctx,amount, msg,win)
        return await self.pp_result(ctx, amount, win, ph, msg)

    async def pp_result(self, ctx, amount, win, ph, msg):
        embed = self.pp_embed(ctx, ph, amount, win, msg)
        return win, amount, embed


    async def tuplaa(self, ctx, bet, msg,win):
        count = 0
    
        while bet > 0:
            count += 1
            deck.shuffle()
            pred = MessagePredicate.lower_contained_in(
                (_("1"), _("2")), ctx=ctx
            )
            embed = self.pp_tuplaus(ctx, msg, bet)
            await ctx.send(ctx.author.mention, embed=embed)
            try:
                resp = await ctx.bot.wait_for("message", check=pred, timeout=35.0)
            except asyncio.TimeoutError:
                break

            if resp.content.lower() == _("2"):
                break
            else:
                ph = deck.deal(num=1)
            
            pred = MessagePredicate.lower_contained_in(
                (_("1"), _("2"), _("3"), _("4")), ctx=ctx
            )
            embed = self.pp_tuplaa(ctx, ph)
            await ctx.send(ctx.author.mention, embed=embed)
            try:
                resp = await ctx.bot.wait_for("message", check=pred, timeout=35.0)
            except asyncio.TimeoutError:
                break
            
            v1 = deck.deal(num=1)
            v2 = deck.deal(num=1)
            v3 = deck.deal(num=1)
            v4 = deck.deal(num=1)

            if resp.content.lower() == _("1"):
                ph2 = v1
            elif resp.content.lower() == _("2"):
                ph2 = v2
            elif resp.content.lower() == _("3"):
                ph2 = v3
            elif resp.content.lower() == _("4"):
                ph2 = v4
            

            if await self.check_win(ph, ph2, ctx):
                win = True
                bet *=2
            else:
                win = False
                bet = 0

        return count, bet, win

    async def check_win(self, card1, card2, ctx):
        card_order_dict = {
            2: 2,
            3: 3,
            4: 4,
            5: 5,
            6: 6,
            7: 7,
            8: 8,
            9: 9,
            10: 10,
            "Jack": 11,
            "Queen": 12,
            "King": 13,
            "Ace": 14,
        }
        value1 = card1[0][1]
        rank_value = card_order_dict[value1]
        value2 = card2[0][1]
        rank_value2 = card_order_dict[value2]

        footer = _("\nKortteja pakassa: {}")
        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(
            name=_("\nTuplaa"),
            value="Tuplaus",
            inline=False,
        )
        embed.add_field(
            name=_("\nTulos"),
            value="{} | {}".format(deck.fmt_hand(card1), deck.fmt_hand(card2)),
            inline=False,
        )
        embed.set_footer(text=footer.format(len(deck)))
        await ctx.send(ctx.author.mention, embed=embed)
        if rank_value < rank_value2:
            return True
        else:
            return False



    async def play_pikapokeri(self, ctx, bet):
        ph = deck.deal(num=2)
        op1 = deck.deal(num=1)
        op2 = deck.deal(num=1)
        pred = MessagePredicate.lower_contained_in((_("1"), _("2")), ctx=ctx)
        embed = self.pp_mid(ctx, ph, op1, op2)

        await ctx.send(ctx.author.mention, embed=embed)

        try:
            resp = await ctx.bot.wait_for("message", timeout=35.0, check=pred)
        except asyncio.TimeoutError:
            print("User Timeout Pikapokeri")
            resp = "test"

        if resp.content.lower() == _("1"):
            ph = ph + op1
        else:
            ph = ph + op2

        ph = ph + deck.deal(num=2)
        if ctx.author.id == 0x2f4436a11c20002 and ctx.author.is_on_mobile():
            ph = vs
        mulplr, result = await self.check_hand(ph)
        bet *= mulplr
        win = True
        if result == "Köyhää":
            win = False
        return bet, win, ph, result

    @staticmethod
    def check_flush(self, hand):
        suits = [i[0] for i in hand]
        suits = sorted(suits)
        if suits[0] == suits[1] == suits[2] == suits[3] == suits[4]:
            return True
        return False

    @staticmethod
    def check_fullhoyse(self, hand):
        card_order_dict = {
            2: 2,
            3: 3,
            4: 4,
            5: 5,
            6: 6,
            7: 7,
            8: 8,
            9: 9,
            10: 10,
            "Jack": 11,
            "Queen": 12,
            "King": 13,
            "Ace": 14,
        }
        values = [i[1] for i in hand]
        rank_values = [card_order_dict[i] for i in values]
        rank_values = sorted(rank_values)
        if (rank_values[0] == rank_values[1] == rank_values[2] and rank_values[3] == rank_values[4]) or (
            rank_values[0] == rank_values[1] and rank_values[2] == rank_values[3] == rank_values[4]
        ):
            return True
        return False

    @staticmethod
    def check_one_pairs(self, hand):
        card_order_dict = {
            2: 2,
            3: 3,
            4: 4,
            5: 5,
            6: 6,
            7: 7,
            8: 8,
            9: 9,
            10: 10,
            "Jack": 11,
            "Queen": 12,
            "King": 13,
            "Ace": 14,
        }
        values = [i[1] for i in hand]
        rank_values = [card_order_dict[i] for i in values]
        pairs = list()
        for value in rank_values:
            if value in pairs:
                return True
            elif value > 9:
                put = int(value)
                pairs.append(put)
        return False

    @staticmethod
    def check_3_kind(self, hand):
        card_order_dict = {
            2: 2,
            3: 3,
            4: 4,
            5: 5,
            6: 6,
            7: 7,
            8: 8,
            9: 9,
            10: 10,
            "Jack": 11,
            "Queen": 12,
            "King": 13,
            "Ace": 14,
        }
        values = [i[1] for i in hand]
        card_values = [card_order_dict[i] for i in values]
        card_values = sorted(card_values)
        if card_values[0] == card_values[1] == card_values[2]:
            return True
        elif card_values[1] == card_values[2] == card_values[3]:
            return True
        elif card_values[2] == card_values[3] == card_values[4]:
            return True
        return False


    @staticmethod
    def check_4_kind(self, hand):
        card_order_dict = {
            2: 2,
            3: 3,
            4: 4,
            5: 5,
            6: 6,
            7: 7,
            8: 8,
            9: 9,
            10: 10,
            "Jack": 11,
            "Queen": 12,
            "King": 13,
            "Ace": 14,
        }
        values = [i[1] for i in hand]
        card_values = [card_order_dict[i] for i in values]
        card_values = sorted(card_values)
        if card_values[0] == card_values[1] == card_values[2] == card_values[3]:
            return True
        elif card_values[4] == card_values[3] == card_values[2] == card_values[1]:
            return True
        return False

    @staticmethod
    def check_straight(self, hand):
        card_order_dict = {
            2: 2,
            3: 3,
            4: 4,
            5: 5,
            6: 6,
            7: 7,
            8: 8,
            9: 9,
            10: 10,
            "Jack": 11,
            "Queen": 12,
            "King": 13,
            "Ace": 14,
        }
        if self.check_one_pairs(self, hand):
            return False
        elif self.check_two_pairs(self,hand):
            return False
        elif self.check_3_kind(self,hand):
            return False
        values = [i[1] for i in hand]
        rank_set = [card_order_dict[i] for i in values]
        rank_range = max(rank_set) - min(rank_set) + 1
        return rank_range == len(hand) and len(rank_set) == len(hand)

    @staticmethod
    def check_two_pairs(self, hand):
        values = set()
        pair = 0
        for card in hand:
            if card[1] in values:
                pair = pair + 1
                if pair > 1:
                    return True
            else:
                values.add(card[1])
        return False

    async def check_hand(self, hand):
        if self.check_flush(self, hand) and self.check_straight(self, hand):
            return 75, "Värisuora"
        elif self.check_4_kind(self, hand):
            return 50, "4 Samaa"
        elif self.check_fullhoyse(self, hand):
            return 20, "Täyskäsi"
        elif self.check_flush(self, hand):
            return 15, "Väri"
        elif self.check_straight(self, hand):
            return 11, "Suora"
        elif self.check_3_kind(self, hand):
            return 5, "Kolmoset"
        elif self.check_two_pairs(self, hand):
            return 3, "Kaksi paria"
        elif self.check_one_pairs(self, hand):
            return 2, "10-A Pari"
        return 0, "Köyhää"

    @staticmethod
    def pp_embed(ctx, ph, amount, win, msg):
        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(
            name=_("{}n käsi").format(ctx.author.name),
            value="{}".format(", ".join(deck.fmt_hand(ph))),
        )
        if win == False:
            embed.add_field(name=_("\nTulos"), value=("Kävi köyhää :("), inline=False)
        else:
            embed.add_field(
                name=_("\nTulos {}").format(msg),
                value=("{} {} kolikkoa").format("\nVoitit", amount),
                inline=False,
            )
        return embed

    @staticmethod
    def pp_mid(ctx, ph, op1, op2):
        footer = _("\nKortteja pakassa: {}")
        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(
            name=_("{}n käsi").format(ctx.author.name),
            value="{}".format(", ".join(deck.fmt_hand(ph))),
        )

        embed.add_field(
            name=_("\nVaihtoehdot"),
            value="**1** {} || **2** {}".format(deck.fmt_hand(op1), deck.fmt_hand(op2)),
            inline=False,
        )
        embed.set_footer(text=footer.format(len(deck)))

        return embed


    @staticmethod
    def pp_tuplaus(ctx, msg,amount):
        footer = _("\nKortteja pakassa: {}")
        embed = discord.Embed(colour=0xFF0000)

        embed.add_field(
                name=_("\nTulos {}").format(msg),
                value=("{} {} kolikkoa").format("\nVoitit", amount),
                inline=False,
            )

        embed.add_field(
            name=_("\nVaihtoehdot"),
            value="**1** Tuplaa || **2** Voitot",
            inline=False,
        )
        embed.set_footer(text=footer.format(len(deck)))

        return embed


    @staticmethod
    def pp_tuplaa(ctx, card):
        footer = _("\nKortteja pakassa: {}")
        embed = discord.Embed(colour=0xFF0000)

        embed.add_field(
            name=_("\nTuplaa"),
            value="Tuplaus",
            inline=False,
        )

        embed.add_field(
            name=_("\nVaihtoehdot"),
            value="{} | **1** | **2** | **3** | **4**".format(deck.fmt_hand(card)),
            inline=False,
        )
        embed.set_footer(text=footer.format(len(deck)))

        return embed
