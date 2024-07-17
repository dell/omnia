Network
=========

⦾ **Why does splitting an ethernet Z series port fail with "Failed. Either port already split with different breakout value or port is not available on ethernet switch"?**

**Potential Cause**:

    1. The port is already split.

    2. It is an even-numbered port.

**Resolution**: Changing the ``breakout_value`` on a split port is currently not supported. Ensure the port is un-split before assigning a new ``breakout_value``.