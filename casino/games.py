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
        await ctx.send(_("You put all your chips into the machine and pull the lever..."))
        await asyncio.sleep(3)
        outcome = random.randint(0, multiplier + 1)
        if outcome == 0:
            msg = "▂▃▅▇█▓▒░ [♠]  [♥]  [♦]  [♣] ░▒▓█▇▅▃▂\n"
            msg += _("          CONGRATULATIONS YOU WON\n")
            msg += _("░▒▓█▇▅▃▂ ⚅ J A C K P O T ⚅ ▂▃▅▇█▓▒░")
            msg = box(msg, lang='py')
            bet *= multiplier
        else:
            msg = _("Nothing happens. You stare at the machine contemplating your decision.")
        return outcome == 0, bet, msg

    @game_engine("Coin", (_("heads"), _("tails")))
    async def play_coin(self, ctx, bet, choice):
        await ctx.send(_("The coin flips into the air..."))
        await asyncio.sleep(2)
        outcome = random.choice((_("heads"), _("tails")))
        msg = _("The coin landed on {}!").format(outcome)
        return choice.lower() in outcome, bet, msg

    @game_engine("Cups", ('1', '2', '3'))
    async def play_cups(self, ctx, bet, choice):
        await ctx.send(_("The cups start shuffling along the table..."))
        await asyncio.sleep(3)
        outcome = random.randint(1, 3)
        msg = _("The coin was under cup {}!").format(outcome)
        return int(choice) == outcome, bet, msg

    @game_engine("Dice")
    async def play_dice(self, ctx, bet):
        await ctx.send(_("The dice strike the back of the table and begin to tumble into "
                         "place..."))
        await asyncio.sleep(2)
        die_one, die_two = self.roll_dice()
        outcome = die_one + die_two

        msg = _("The dice landed on {} and {} ({}).").format(die_one, die_two, outcome)
        return outcome in (2, 7, 11, 12), bet, msg

    @game_engine("Hilo", (_("low"), _("lo"), _('high'), _('hi'), _('seven'), _('7')))
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

        await ctx.send("{}\nI'll roll the dice one more time. This time you will need exactly "
                       "{} to win.".format(msg.format(d1, d2), d1 + d2))
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
            choice = await ctx.bot.wait_for('message', check=condition1, timeout=35.0)
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
            await ctx.send(_("{} You can not cover the bet. Please choose "
                             "hit or stay.").format(ctx.author.mention))

            try:
                choice2 = await ctx.bot.wait_for('message', check=condition2, timeout=35.0)
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
        if deck.hand_check(dh, 'Ace') and count != 21:
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
        embed.add_field(name=_("{}'s Hand").format(ctx.author.name),
                        value=hand.format(", ".join(deck.fmt_hand(ph)), count1))
        embed.add_field(name=_("{}'s Hand").format(ctx.bot.user.name),
                        value=hand.format(dealer_hand, count2))
        embed.add_field(name='\u200b', value=options, inline=False)
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

        await ctx.send(_("The dealer shuffles the deck and deals 2 cards face down. One for the "
                         "player and one for the dealer..."))
        await asyncio.sleep(2)
        await ctx.send(_("**FLIP!**"))
        await asyncio.sleep(1)

        if pc != dc:
            if pc >= dc:
                outcome = "Win"
            else:
                outcome = "Loss"
            return outcome, player_card, dealer_card, bet

        await ctx.send(_("The player and dealer are both showing a **{}**!\nTHIS MEANS "
                         "WAR! You may choose to surrender and forfeit half your bet, or "
                         "you can go to war.\nIf you go to war your bet will be doubled, "
                         "but the multiplier is only applied to your original bet, the rest will "
                         "be pushed.").format(deck.fmt_card(player_card)))
        pred = MessagePredicate.lower_contained_in((_("war"), _("surrender"), _("ffs")), ctx=ctx)
        try:
            choice = await ctx.bot.wait_for('message', check=pred, timeout=35.0)
        except asyncio.TimeoutError:
            return "Surrender", player_card, dealer_card, bet

        if choice is None or choice.content.title() in (_("Surrender"), _("Ffs")):
            outcome = "Surrender"
            bet /= 2
            return outcome, player_card, dealer_card, bet
        else:
            player_card, dealer_card, pc, dc = self.burn_and_draw()

            await ctx.send(_("The dealer burns three cards and deals two cards face down..."))
            await asyncio.sleep(3)
            await ctx.send(_("**FLIP!**"))

            if pc >= dc:
                outcome = "Win"
            else:
                outcome = "Loss"
            return outcome, player_card, dealer_card, bet

    @staticmethod
    async def war_results(outcome, player_card, dealer_card, amount):
        msg = _("**Player Card:** {}\n**Dealer Card:** {}\n"
                "").format(deck.fmt_card(player_card), deck.fmt_card(dealer_card))
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

            pred = MessagePredicate.lower_contained_in((_("double"), _("cash out")), ctx=ctx)

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
        embed.add_field(name=_("{}'s Score").format(ctx.author.name),
                        value=score)
        embed.add_field(name='\u200b', value=options, inline=False)
        if not outcome:
            embed.add_field(name='\u200b', value='Remember, you can cash out at anytime.',
                            inline=False)
        embed.set_footer(text='Try again and test your luck!')
        return embed


class Pikapokeri:
    """Pikapokeri"""


    def __init__(self):
        super().__init__()

    @game_engine("Pikapokeri")
    async def play(self, ctx, bet):
        ctx.send("Pikapokeri")
        amount,win, ph = await self.play_pikapokeri(ctx, bet)
        return await self.pp_result(ctx, amount,win,ph)
        
    async def pp_result(self, ctx, amount,win,ph):
        embed = self.pp_embed(ctx,ph,amount,win)
        result = True
        if win == None:
            result = False
         
        return result, amount, embed


    async def play_pikapokeri(self, ctx, bet):
        ph = deck.deal(num=2)
        op1 = deck.deal(num=1)
        op2 = deck.deal(num=1)

        embed = self.pp_mid(ctx, ph,op1,op2)
        await ctx.send(ctx.author.mention, embed=embed)

        try:
            resp = await ctx.bot.wait_for("message", timeout=35.0)
        except asyncio.TimeoutError:
            resp.content = "2"

        if resp.content.lower() == _("1"):
            ph = ph+op1
        else:
            ph = ph+op2
            
        ph = ph + deck.deal(num=2)
        mulplr, result = await self.check_hand(ph)
        bet *= mulplr
        win = True
        if result == None:
            win = False
        return bet, win, ph

    async def check_flush(self, hand):
        suits = ["clubs", "diamonds", "spades", "hearts"]
        for suit in suits:
            test = 0
            for card in hand:
                if suit in card[0]:
                    test = test+1
                    if test == 5:
                        return True
        return False

    async def check_one_pairs(self, hand):
        card_order_dict = {2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:10,"Jack":11, "Queen":12, "King":13, "Ace":14}
        values = [i[1] for i in hand]
        rank_values = [card_order_dict[i] for i in values]
        pairs = list()
        for value in rank_values:
            if value in pairs and sum(pairs) > 20:
                return True
            else:
                put = int(value)
                pairs.append(put)
        return False

    async def check_3_kind(self, hand):
        values = set()
        num = 0
        for card in hand:
            if card[1] in values:
                num = num+1
                if num == 3:
                    return True
            else:
                values.add(card[1])
        return False

    async def check_4_kind(self, hand):
        values = set()
        num = 0
        for card in hand:
            if card[1] in values:
                num = num+1
                if num == 4:
                    return True
            else:
                values.add(card[1])
        return False

    async def check_straight(self, hand):
        card_order_dict = {2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:10,"Jack":11, "Queen":12, "King":13, "Ace":14}
        values = [i[1] for i in hand]
        rank_values = [card_order_dict[i] for i in values]
        value_range = max(rank_values) - min(rank_values)
        if value_range == 4 and await self.check_one_pairs(hand) == False:
            return True
        else: 
            #check straight with low Ace
            if set(values) == set(["Ace", "2", "3", "4", "5"]):
                return True
            return False

    async def check_two_pairs(self, hand):
        values = set()
        pair = 0
        for card in hand:
            if card[1] in values:
                pair = pair+1
                if pair > 3:
                    return True
            else:
                values.add(card[1])
        return False

    async def check_hand(self, hand):
        if await self.check_flush(hand) and await self.check_straight(hand):
            print("Värisuora")
            return 75, "Värisuora"
        elif await self.check_4_kind(hand):
            print("4 Samaa")
            return 50, "4 Samaa"
        elif await self.check_flush(hand):
            print("Väri")
            return 15, "Väri"
        elif await self.check_straight(hand):
            print("Suora")
            return 11, "Suora"
        elif await self.check_3_kind(hand):
            print("Kolmoset")
            return 5, "Kolmoset"
        elif await self.check_two_pairs(hand):
            print("Kaksi paria")
            return 3, "Kaksi paria"
        elif await self.check_one_pairs(hand):
            print("10-A Pari")
            return 2, "10-A Pari"
        return 0

    @staticmethod
    def pp_embed(ctx, ph, amount, win):
        footer = _("Kortteja pakassa: {}")
        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(name=_("{}'s Hand").format(ctx.author.name),
                        value="{}".format(", ".join(deck.fmt_hand(ph))))
        if win:
            embed.add_field(name=_("Tulos"),value=("Hävisit :("))           
        else:
            embed.add_field(name=_("Tulos"),value=("{}, {}").format("Voitit", amount))
        embed.set_footer(text=footer.format(len(deck)))
        return embed

    @staticmethod
    def pp_mid(ctx, ph,op1,op2):
        footer = _("Kortteja pakassa: {}")
        embed = discord.Embed(colour=0xFF0000)
        embed.add_field(name=_("{}'s Hand").format(ctx.author.name),
                        value="{}".format(", ".join(deck.fmt_hand(ph))))
        
        embed.add_field(name=_("Vaihtoehdot"),
                        value="1:{} 2:{}".format(deck.fmt_hand(op1), deck.fmt_hand(op2)))    
        embed.set_footer(text=footer.format(len(deck)))       
        
        return embed