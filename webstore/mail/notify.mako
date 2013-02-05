You receive new order!

% if echeck:
    Payed by Echeck, wait for clear.

% else:
    % if new:
        New License ID is: ${regid}

    % else:
        Upgrade for License ID: ${regid}

    % endif
% endif

Products Purchased:
% for item in order.items:
        ${item.product.name}
% endfor

Order #${order.order_id}, Total: $${'%.2f'%order.total}
