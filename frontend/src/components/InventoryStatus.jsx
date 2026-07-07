import React, { useState } from 'react';
import api from '../services/api';

export default function InventoryStatus({ inventory = [], onInventoryUpdate }) {
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedMed, setSelectedMed] = useState(null);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [updateMed, setUpdateMed] = useState(null);
  const [newQuantity, setNewQuantity] = useState('');

  // Transform backend inventory format to display format
  const items = inventory.length > 0
    ? inventory.map((item, index) => ({
      id: index + 1,
      name: item.med_name || item.name || 'Unknown',
      count: item.quantity || 0,
      total: Math.max(item.quantity || 0, (item.low_stock_threshold || 10) * 3),
      unit: 'pills'
    }))
    : [];

  const getStatusColor = (count, total) => {
    const percentage = (count / total) * 100;
    if (percentage < 20) return 'var(--danger-color)';
    if (percentage < 40) return 'var(--accent-color)';
    return 'var(--secondary-color)';
  };

  const handleBuyNow = async (medName) => {
    setSelectedMed(medName);
    setLoading(true);
    setShowModal(true);
    setSearchResults([]);

    try {
      const data = await api.searchPharmacy(medName);
      setSearchResults(data.results || []);
    } catch (error) {
      console.error('Failed to search pharmacies:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSearchResults([]);
    setSelectedMed(null);
  };

  const handleUpdateStock = (medName, currentQty) => {
    setUpdateMed(medName);
    setNewQuantity(currentQty.toString());
    setShowUpdateModal(true);
  };

  const handleCloseUpdateModal = () => {
    setShowUpdateModal(false);
    setUpdateMed(null);
    setNewQuantity('');
  };

  const handleSubmitUpdate = async () => {
    if (!newQuantity || isNaN(newQuantity) || parseInt(newQuantity) < 0) {
      alert('Please enter a valid quantity (0 or greater)');
      return;
    }

    setLoading(true);
    try {
      await api.updateInventory(updateMed, parseInt(newQuantity));
      handleCloseUpdateModal();
      // Trigger parent refresh
      if (onInventoryUpdate) {
        onInventoryUpdate();
      }
    } catch (error) {
      console.error('Failed to update inventory:', error);
      alert('Failed to update inventory. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="inventory-status card">
      <ul className="inventory-list">
        {items.map((item) => {
          const color = getStatusColor(item.count, item.total);
          const percentage = (item.count / item.total) * 100;
          const isLow = percentage < 20;

          return (
            <li key={item.id} className="inventory-item">
              <div className="item-header">
                <span className="item-name">{item.name}</span>
                <span className="item-count" style={{ color: isLow ? color : 'inherit' }}>
                  {item.count} left
                </span>
              </div>
              <div className="progress-bar-bg">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${percentage}%`, backgroundColor: color }}
                ></div>
              </div>
              <div className="inventory-actions">
                {isLow && (
                  <div className="low-stock-actions">
                    <span className="low-stock-warning">⚠️ Low Stock - Refill soon</span>
                    <button
                      className="btn-buy-now"
                      onClick={() => handleBuyNow(item.name)}
                    >
                      Buy Now 🛒
                    </button>
                  </div>
                )}
                <button
                  className="btn-update-stock"
                  onClick={() => handleUpdateStock(item.name, item.count)}
                >
                  Update Stock 📦
                </button>
              </div>
            </li>
          );
        })}
      </ul>

      {showModal && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Buy {selectedMed}</h3>
              <button className="btn-close" onClick={handleCloseModal}>&times;</button>
            </div>

            <div className="modal-body">
              {loading ? (
                <div className="loading-spinner">Searching pharmacies...</div>
              ) : searchResults.length > 0 ? (
                <div className="pharmacy-results">
                  {searchResults.map((result, idx) => (
                    <a
                      key={idx}
                      href={result.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="pharmacy-option"
                    >
                      <div className="pharmacy-info">
                        <strong>{result.name}</strong>
                        <span className="delivery-time">🚚 {result.delivery_time}</span>
                      </div>
                      <div className="pharmacy-price">
                        <span className="btn-visit">Visit Store →</span>
                      </div>
                    </a>
                  ))}
                </div>
              ) : (
                <p>No online purchasing options found. Please check local pharmacy.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {showUpdateModal && (
        <div className="modal-overlay" onClick={handleCloseUpdateModal}>
          <div className="modal-content update-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Update Stock - {updateMed}</h3>
              <button className="btn-close" onClick={handleCloseUpdateModal}>&times;</button>
            </div>

            <div className="modal-body">
              <div className="update-form">
                <label htmlFor="quantity-input">New Quantity:</label>
                <input
                  id="quantity-input"
                  type="number"
                  min="0"
                  value={newQuantity}
                  onChange={(e) => setNewQuantity(e.target.value)}
                  placeholder="Enter quantity"
                  autoFocus
                />
                <button
                  className="btn-submit-update"
                  onClick={handleSubmitUpdate}
                  disabled={loading}
                >
                  {loading ? 'Updating...' : 'Update Stock'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .inventory-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .inventory-item {
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        .inventory-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        .item-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }
        .progress-bar-bg {
            height: 8px;
            background: #e2e8f0;
            border-radius: 9999px;
            overflow: hidden;
        }
        .progress-bar-fill {
            height: 100%;
            border-radius: 9999px;
            transition: width 0.3s ease;
        }
        .low-stock-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.75rem;
        }
        .low-stock-warning {
            color: var(--danger-color);
            font-size: 0.875rem;
            font-weight: 500;
        }
        .btn-buy-now {
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.8rem;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.2s;
        }
        .btn-buy-now:hover {
            background: var(--primary-hover);
        }
        
        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal-content {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            width: 90%;
            max-width: 450px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.5rem;
        }
        .modal-header h3 { margin: 0; }
        .btn-close {
            background: transparent;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #666;
        }
        .pharmacy-results {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        .pharmacy-option {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            text-decoration: none;
            color: inherit;
            transition: all 0.2s;
        }
        .pharmacy-option:hover {
            border-color: var(--primary-color);
            background: #f8fafc;
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .pharmacy-info {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
        .delivery-time {
            font-size: 0.8rem;
            color: #64748b;
        }
        .pharmacy-price {
            text-align: right;
        }
        .price-tag {
            display: block;
            font-weight: 700;
            color: var(--secondary-color);
            font-size: 1.1rem;
        }
        .btn-visit {
            font-size: 0.8rem;
            color: var(--primary-color);
            font-weight: 600;
        }
        .loading-spinner {
            text-align: center;
            padding: 2rem;
            color: #64748b;
        }
        .inventory-actions {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            margin-top: 0.75rem;
        }
        .btn-update-stock {
            background: var(--secondary-color);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.875rem;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
            width: 100%;
        }
        .btn-update-stock:hover {
            background: #059669;
            transform: translateY(-1px);
        }
        .update-modal {
            max-width: 400px;
        }
        .update-form {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .update-form label {
            font-weight: 600;
            color: var(--text-color);
        }
        .update-form input {
            padding: 0.75rem;
            border: 2px solid var(--border-color);
            border-radius: 6px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }
        .update-form input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .btn-submit-update {
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-submit-update:hover:not(:disabled) {
            background: #2563eb;
            transform: translateY(-1px);
        }
        .btn-submit-update:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
