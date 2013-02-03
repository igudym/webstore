You receive new order!


% if new:
    New License ID is: ${regid}

% else:
    Upgrade for License ID: ${regid}

% endif

Products Purchased:
% for item in order.items:
        ${item.product.name}
% endfor

Order #${order.order_id}, Total: $${'%.2f'%order.total}
