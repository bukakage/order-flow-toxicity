# order-flow-toxicity-monitor
Order Flow Toxicity monitor through the VPIN

1minute ийн дата IB ээс тодорхой түүхээр татаад stream хийж залгана
- timebar, timebar frequency
- volume bar, volume bar threshold
- dollar bar, dollar bar threshold

Inputs
- Futures Symbols , нэмж хасах
- Trigger threshold

VPIN inputs
- sigma window
- dof
- volume window
- vpin window
- dashed treshold level, 0.8

Telegram token config авдаг байх

1m ohlcv from ib realtime PyQT window дээрээ харуулдаг байх

trigger үүсвэл telegram руу шидэх


# References

    - VPIN paper
        https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1695041

    - Order Flow Toxicity Youtube
        https://www.youtube.com/watch?v=0vPMZXGHMpc

    - Volume Bar, Dollar Volume Bar generation
        https://github.com/BlackArbsCEO/Adv_Fin_ML_Exercises/blob/master/notebooks/Tick%2C%20Volume%2C%20Dollar%20Volume%20Bars.ipynb

    - Tweet about VPIN
        https://x.com/nincazax/status/1819472102686445888