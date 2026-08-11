"""
engine/market_engine.py

BMIE Market Engine

Responsibilities
----------------
- Run multi-timeframe analysis
- Build MTF context
- Generate trade decision
- Validate entry conditions
- Run entry confirmation
- Select best Order Block
- Select best Liquidity
- Evaluate Setup Quality
- Generate risk plan
- Print concise market report

Author: BMIE Project
"""


from types import SimpleNamespace

from analyzer import analyze_market


from config import (
    TIMEFRAMES,
    RISK_PER_TRADE,
    MINIMUM_RISK_REWARD,
)


from models import (
    MarketAnalysis,
    MultiTimeframeContext,
)


from smc.confluence import ConfluenceEngine

from smc.entry_validator import EntryValidator

from smc.entry_confirmation import EntryConfirmationEngine

from smc.risk_manager import RiskManager

from smc.liquidity import LiquidityEngine

from smc.setup_quality import SetupQualityEngine

from journal.trade_journal import TradeJournal
from backtest.analysis_cache import AnalysisCache





class MarketEngine:



    def __init__(
    self,
    session,
    market_data=None,
    backtest=False,
    analysis_cache=None
   ):


        self.session = session

        self.market_data = market_data

        self.analysis_cache = analysis_cache

        self.backtest = backtest

        self.analysis = MarketAnalysis()


        self.selected_order_block = None


        self.selected_liquidity = None

        self.target_liquidity = None


        self.setup_quality = None


        self.entry_confirmation = None

        self.trade_journal = None if backtest else TradeJournal()





    # ======================================================
    # Select Best Order Block
    # ======================================================

    def select_order_block(self):


        """
        Select OB using SMC priority.

        Priority:

        1H Trend
        15M Setup
        5M Entry
        """


        priority = [

            self.analysis.trend,

            self.analysis.setup,

            self.analysis.entry,

        ]



        for result in priority:



            if result and result.order_blocks:



                return sorted(

                    result.order_blocks,

                    key=lambda x: x.created_at,

                    reverse=True

                )[0]



        return None





    # ======================================================
    # Select Best Liquidity
    # ======================================================

    def select_liquidity(
        self,
        direction
    ):


        entry = self.analysis.entry



        if not entry:

            return None



        if not hasattr(

            entry,

            "swing_highs"

        ):

            return None



        if not hasattr(

            entry,

            "swing_lows"

        ):

            return None



        liquidity_engine = LiquidityEngine(

            entry.swing_highs,

            entry.swing_lows,

            entry.df

        )



        all_liquidity = liquidity_engine.analyze()



        return liquidity_engine.get_best_liquidity(

            all_liquidity,

            entry.current_price,

            direction

        )


# ================= PART 1 END =================

# ================= PART 2 START =================


    # ======================================================
    # Select Target Liquidity
    # ======================================================

    def select_target_liquidity(
        self,
        direction,
        entry_price
    ):

        entry = self.analysis.entry

        if not entry:
            return None


        if entry_price is None:
            return None

        print(
            "TARGET DEBUG:",
            "direction=",
            direction,
            "entry_price=",
            entry_price
        )


        liquidity_engine = LiquidityEngine(

            entry.swing_highs,

            entry.swing_lows,

            entry.df

        )


        zones = liquidity_engine.analyze()


        candidates = []


        for zone in zones:

            print(
                "ZONE DEBUG:",
                "side=",
                zone.side,
                "level=",
                zone.level
            )



            if direction == "Bullish":


                # Bullish target must be above entry

                if zone.side != "Buy-side":
                    continue


                if zone.level <= entry_price:
                    continue



            elif direction == "Bearish":


                # Bearish target must be below entry

                if zone.side != "Sell-side":
                    continue


                if zone.level >= entry_price:
                    continue



            candidates.append(zone)



        if candidates:

            return sorted(

                candidates,

                key=lambda x: abs(entry_price - x.level)

            )[0]



        # ==================================================
        # Swing fallback
        # ==================================================

        if direction == "Bullish":


            highs = [

                x.price

                for x in entry.swing_highs

                if x.price > entry_price

            ]


            if highs:

                return SimpleNamespace(

                    level=min(highs)

                )



        if direction == "Bearish":


            lows = [

                x.price

                for x in entry.swing_lows

                if x.price < entry_price

            ]


            if lows:

                return SimpleNamespace(

                    level=max(lows)

                )



        # No valid directional target

        return None


    # ======================================================
    # Run Analysis
    # ======================================================

    def run(self):


        print(

            "\nRunning Multi-Timeframe Analysis..."

        )



        print(

            "-" * 60

        )



        for name, timeframe in TIMEFRAMES.items():



            print(

                f"Analyzing {name.upper()} ({timeframe})..."

            )
            # Cache only higher timeframe analysis.
            # 1D, 4H and 1H use cache.
            # 15M and 5M recalculate every candle.

            cache_timeframes = [
                "1d",
                "4h",
                "1h"
            ]

            result = None

            if (
                name in cache_timeframes
                and self.analysis_cache
            ):

                result = self.analysis_cache.load(
                    name
                )

            if result is None:

                result = analyze_market(

                    self.session,

                    timeframe,

                    df=self.market_data.get(timeframe)
                    if self.market_data
                    else None,

                )

                if (
                    name in cache_timeframes
                    and self.analysis_cache
                ):

                    self.analysis_cache.save(
                        name,
                        result
                    )

            setattr(

                self.analysis,

                name,

                result

            )



        print(

            "\nAnalysis Completed Successfully."

        )





        # ==================================================
        # Select Institutional Order Block
        # ==================================================

        self.selected_order_block = (

            self.select_order_block()

        )





        # ==================================================
        # Multi Timeframe Context
        # ==================================================

        context = MultiTimeframeContext(

            bias=self.analysis.bias,

            structure=self.analysis.structure,

            trend=self.analysis.trend,

            setup=self.analysis.setup,

            entry=self.analysis.entry,

        )





        # ==================================================
        # Confluence Engine
        # ==================================================

        confluence_engine = ConfluenceEngine(

            context

        )



        trade_decision = (

            confluence_engine.analyze()

        )





        # ==================================================
        # Select Best Liquidity
        # ==================================================

        direction = "Bullish"



        if trade_decision.signal in [

            "SELL",

            "STRONG SELL"

        ]:


            direction = "Bearish"

        # Attach direction for RiskManager
        trade_decision.direction = direction



        self.selected_liquidity = (

            self.select_liquidity(

                direction

            )

        )


        # ==================================================
        # Calculate Trade Entry Price From Order Block
        # ==================================================

        entry_price = None


        if self.selected_order_block:

            entry_price = (

                self.selected_order_block.high +

                self.selected_order_block.low

            ) / 2



        self.target_liquidity = (

            self.select_target_liquidity(

                direction,
                entry_price

            )

        )

        print(
            "AFTER TARGET SELECTION:",
            self.target_liquidity
        )





        # ==================================================
        # Setup Quality Evaluation
        # ==================================================

        latest_fvg = None



        if self.analysis.entry:



            if self.analysis.entry.fair_value_gaps:



                latest_fvg = sorted(

                    self.analysis.entry.fair_value_gaps,

                    key=lambda x: x.created_at,

                    reverse=True

                )[0]





        quality_engine = SetupQualityEngine(

            context=context,

            order_block=self.selected_order_block,

            liquidity=self.selected_liquidity,

            fvg=latest_fvg,

        )



        self.setup_quality = (

            quality_engine.analyze()

        )





        entry = self.analysis.entry



        if entry:



            # ==================================================
            # Prepare Order Block List
            # ==================================================

            order_blocks = []



            if self.selected_order_block:



                order_blocks.append(

                    self.selected_order_block

                )





            # ==================================================
            # Entry Validation
            # ==================================================

            entry_validator = EntryValidator(

                current_price=entry.current_price,

                trade_decision=trade_decision,

                order_blocks=order_blocks,

                fair_value_gaps=entry.fair_value_gaps,

                liquidity=[self.selected_liquidity]

                if self.selected_liquidity

                else [],

                entry_context=self.analysis.entry,

                setup_context=self.analysis.setup,

                trend_context=self.analysis.trend,

            )





            validation = (

                entry_validator.analyze()

            )





            # ==================================================
            # Entry Confirmation
            # ==================================================

            confirmation_engine = EntryConfirmationEngine(

                current_price=entry.current_price,

                direction=entry_validator.get_direction(),

                order_blocks=order_blocks,

                fair_value_gaps=entry.fair_value_gaps,

                liquidity=[self.selected_liquidity]

                if self.selected_liquidity

                else [],

                entry_context=self.analysis.entry,

            )



            confirmation = (

                confirmation_engine.analyze()

            )



            self.entry_confirmation = confirmation



            entry.entry_confirmation = confirmation





            if not validation["valid"]:


                trade_decision.signal = (

                    validation["status"]

                )



            trade_decision.reasons.extend(

                validation["reasons"]

            )



            trade_decision.reasons.extend(

                confirmation["reasons"]

            )



            # ==================================================
            # Attach Direction To Trade Decision
            # ==================================================

            entry_direction = entry_validator.get_direction()


            if entry_direction:

                trade_decision.direction = entry_direction



            entry.trade_decision = trade_decision

            # ==================================================
            # Trade Journal Save
            # ==================================================

            journal_entry = self.trade_journal.create_entry(

                self.session,

                self.analysis,

                self.setup_quality,

                self.entry_confirmation,
                entry.trade_decision,

                entry.risk_decision,

            )


            if self.trade_journal:

                self.trade_journal.save_trade(

                    journal_entry

                )



# ================= PART 2 END =================

# ================= PART 3 START =================


        # ==================================================
        # Risk Management
        # ==================================================

        allowed_signals = [

            "BUY",

            "SELL",

            "STRONG BUY",

            "STRONG SELL",

            "WAIT FOR CONFIRMATION",

            "WAIT FOR RETRACEMENT",

        ]



        confirmation_status = None

        if self.entry_confirmation:
            confirmation_status = self.entry_confirmation.get(
                "status",
                ""
            )


        if (
            trade_decision.signal in allowed_signals
            or
            confirmation_status in [
                "WAIT FOR CONFIRMATION",
                "WAIT FOR RETRACEMENT",
                "ENTRY CONFIRMED"
            ]
        ):

            



            risk_manager = RiskManager(

                account_balance=self.session.balance,

                risk_percent=RISK_PER_TRADE,

                minimum_rr=MINIMUM_RISK_REWARD,

            )

            if not self.backtest:

                print(
                "TRADE DECISION DEBUG:",
                trade_decision.signal,
                getattr(trade_decision, "direction", None),
                vars(trade_decision)
            )
            

            risk_decision = risk_manager.analyze(

                trade_decision,

                order_blocks,

                liquidity=self.target_liquidity,

            )



            entry.risk_decision = risk_decision

            # Sync risk decision with analysis object
            self.analysis.entry.risk_decision = risk_decision


            # ==================================================
            # Trade Journal Save
            # ==================================================

            journal_entry = self.trade_journal.create_entry(

                self.session,
                self.analysis,
                self.setup_quality,
                self.entry_confirmation,
                entry.trade_decision,
                entry.risk_decision,

            )


            if self.trade_journal:

                self.trade_journal.save_trade(

                    journal_entry

                )



        else:

           if not hasattr(entry, "risk_decision"):

               entry.risk_decision = None





    # ======================================================
    # Helpers
    # ======================================================

    @staticmethod
    def format_event(event):


        if event is None:

            return "None"



        if event.direction is None:

            return "None"



        return event.direction





    @staticmethod
    def latest_fvg(result):


        if not result:

            return None



        if not result.fair_value_gaps:

            return None



        return sorted(

            result.fair_value_gaps,

            key=lambda x: x.created_at,

            reverse=True

        )[0]





    # ======================================================
    # Report
    # ======================================================

    def print_report(self):


        entry = self.analysis.entry



        print("\n")

        print("=" * 60)

        print("BMIE MARKET INTELLIGENCE REPORT")

        print("=" * 60)



        print(

            f"Symbol : {self.session.symbol}"

        )



        if entry:


            print(

                f"Price  : {entry.current_price:.2f}"

            )



        print()



        print("-" * 60)

        print("MULTI TIMEFRAME STRUCTURE")

        print("-" * 60)



        for name, result in self.analysis.as_dict().items():


            if result is None:

                continue



            phase = "Unknown"

            event = "None"



            if hasattr(result, "market_state"):


                phase = result.market_state.phase

                event = result.market_state.active_event



            print(

                f"{name.upper():10}: "

                f"{phase} | {event}"

            )



        if entry is None:

            return



        print()

        print("-" * 60)

        print("ACTIVE SETUP")

        print("-" * 60)



        if hasattr(entry, "market_state"):


            print(

                f"Phase      : "

                f"{entry.market_state.phase}"

            )


            print(

                f"Reason     : "

                f"{entry.market_state.reason}"

            )



        print(

            f"BOS        : "

            f"{self.format_event(entry.bos)}"

        )



        print(

            f"CHoCH      : "

            f"{self.format_event(entry.choch)}"

        )



        # ==================================================
        # Order Block
        # ==================================================

        print()



        if self.selected_order_block:


            ob = self.selected_order_block



            print("Order Block")



            print(

                f"Type       : {ob.direction}"

            )



            print(

                f"Zone       : "

                f"{ob.low:.2f} - {ob.high:.2f}"

            )



            print(

                f"Time       : {ob.created_at}"

            )



            if hasattr(ob, "status"):


                print(

                    f"Status     : {ob.status}"

                )



            if hasattr(ob, "strength"):


                print(

                    f"Strength   : {ob.strength}%"

                )



            if hasattr(ob, "distance"):


                print(

                    f"Distance   : {ob.distance}"

                )


# ================= PART 3 END =================

# ================= PART 4 START =================


        # ==================================================
        # Selected Liquidity
        # ==================================================

        print()



        if self.selected_liquidity:


            liquidity = self.selected_liquidity



            print("Liquidity")



            print(

                f"Side       : {liquidity.side}"

            )



            print(

                f"Level      : "

                f"{liquidity.level:.2f}"

            )



            print(

                f"Swept      : "

                f"{liquidity.swept}"

            )



            print(

                f"Valid      : "

                f"{liquidity.sweep_valid}"

            )



            if liquidity.sweep_time:


                print(

                    f"Sweep Time : "

                    f"{liquidity.sweep_time}"

                )



            if liquidity.sweep_price:


                print(

                    f"Sweep Price: "

                    f"{liquidity.sweep_price:.2f}"

                )



            if liquidity.distance_from_price:


                print(

                    f"Distance   : "

                    f"{liquidity.distance_from_price:.2f}"

                )



            print(

                f"Strength   : "

                f"{liquidity.strength}%"

            )





        # ==================================================
        # Setup Quality
        # ==================================================

        print()



        if self.setup_quality:


            print("SETUP QUALITY")

            print("-" * 60)



            print(

                f"Score : "

                f"{self.setup_quality.score}/100"

            )



            print(

                f"Grade : "

                f"{self.setup_quality.grade}"

            )



            print()



            print("Strengths:")



            for item in self.setup_quality.strengths:


                print(

                    f"- {item}"

                )



            print()



            print("Warnings:")



            for item in self.setup_quality.warnings:


                print(

                    f"- {item}"

                )





        # ==================================================
        # Entry Confirmation
        # ==================================================

        print()



        if self.entry_confirmation:


            print("ENTRY CONFIRMATION")

            print("-" * 60)



            print(

                f"Status     : "

                f"{self.entry_confirmation.get('status')}"

            )



            print(

                f"Confidence : "

                f"{self.entry_confirmation.get('confidence', 0)}%"

            )



            print()



            print("Reasons:")



            for reason in self.entry_confirmation.get(

                "reasons",

                []

            ):


                print(

                    f"- {reason}"

                )





        # ==================================================
        # FVG
        # ==================================================

        fvg = self.latest_fvg(entry)



        print()



        if fvg:


            print("FVG")



            print(

                f"Type       : {fvg.direction}"

            )



            print(

                f"Zone       : "

                f"{fvg.low:.2f} - {fvg.high:.2f}"

            )



            print(

                f"Filled     : "

                f"{fvg.filled}"

            )





        # ==================================================
        # Trade Decision
        # ==================================================

        print()



        print("-" * 60)

        print("TRADE DECISION")

        print("-" * 60)



        decision = entry.trade_decision



        if decision:


            print(

                f"Signal     : "

                f"{decision.signal}"

            )



            print(

                f"Confidence : "

                f"{decision.confidence:.2f}%"

            )



            print()



            print("Reasons:")



            for reason in list(dict.fromkeys(decision.reasons)):


                print(

                    f"- {reason}"

                )



        else:


            print(

                "Decision unavailable"

            )





        # ==================================================
        # Risk Plan
        # ==================================================

        print()

        print("-" * 60)

        print("RISK PLAN")

        print("-" * 60)



        risk = entry.risk_decision



        if risk and risk.stop_loss:


            print(

                f"Entry Zone : "

                f"{risk.entry:.2f}"

            )



            print(

                f"Stop Loss  : "

                f"{risk.stop_loss:.2f}"

            )



            print(

                f"Target     : "

                f"{risk.target:.2f}"

            )



            print(

                f"Risk Reward: "

                f"{risk.risk_reward:.2f}"

            )



            print(

                f"Risk Amount: ₹"

                f"{risk.risk_amount:.2f}"

            )



            print(

                f"Position   : "

                f"{risk.position_size:.2f}"

            )



        else:


            print(

                "Risk plan unavailable"

            )



        print("=" * 60)



        print(

            "BMIE analysis completed."

        )


# ================= PART 4 END =================
