import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiState = vi.hoisted(() => ({
  inventoryApiClient: {
    delete: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
  transactionApiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('@/services/api', () => apiState)

describe('product service', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    window.localStorage.clear()
    apiState.inventoryApiClient.delete.mockResolvedValue({})
    apiState.inventoryApiClient.put.mockImplementation((url, payload) => Promise.resolve({
      data: {
        id: Number(String(url).split('/').pop()),
        title: 'Camera',
        price: 120,
        ...payload,
      },
    }))
  })

  it('loads product detail from the catalog first to avoid forbidden detail requests', async () => {
    const { getProductById } = await import('@/services/product.service')

    apiState.inventoryApiClient.get.mockResolvedValueOnce({
      data: [
        {
          id: 2,
          title: 'Camera',
          price: 120,
          owner_id: 'seller@example.com',
        },
      ],
    })

    await expect(getProductById(2)).resolves.toMatchObject({
      id: 2,
      title: 'Camera',
      seller_id: 'seller@example.com',
    })

    expect(apiState.inventoryApiClient.get).toHaveBeenCalledTimes(1)
    expect(apiState.inventoryApiClient.get).toHaveBeenCalledWith(
      '/products',
      expect.objectContaining({
        params: {},
      }),
    )
  })

  it('falls back to the detail endpoint only when the product is missing from the catalog', async () => {
    const { getProductById } = await import('@/services/product.service')

    apiState.inventoryApiClient.get
      .mockResolvedValueOnce({
        data: [],
      })
      .mockResolvedValueOnce({
        data: {
          id: 2,
          title: 'Camera',
          price: 120,
          seller_id: 'seller@example.com',
        },
      })

    await expect(getProductById('2')).resolves.toMatchObject({
      id: 2,
      title: 'Camera',
      seller_id: 'seller@example.com',
    })

    expect(apiState.inventoryApiClient.get).toHaveBeenNthCalledWith(
      1,
      '/products',
      expect.objectContaining({
        params: {},
      }),
    )
    expect(apiState.inventoryApiClient.get).toHaveBeenNthCalledWith(2, '/products/2')
  })

  it('keeps the original forbidden error when the product is not in the catalog', async () => {
    const { getProductById } = await import('@/services/product.service')
    const forbiddenError = {
      response: {
        status: 403,
      },
    }

    apiState.inventoryApiClient.get
      .mockResolvedValueOnce({
        data: [],
      })
      .mockRejectedValueOnce(forbiddenError)

    await expect(getProductById(2)).rejects.toBe(forbiddenError)
  })

  it('creates matching inventory and transaction products and stores their ID mapping', async () => {
    const { createProduct, getProductById } = await import('@/services/product.service')
    const payload = {
      title: 'Camera',
      description: 'Good camera',
      category: 'Electronics',
      price: 120,
      condition: 'Good',
    }

    apiState.inventoryApiClient.get.mockResolvedValueOnce({
      data: [
        {
          id: 7,
          title: 'Camera',
          price: 120,
          transaction_product_id: 15,
        },
      ],
    })
    apiState.inventoryApiClient.post.mockResolvedValueOnce({
      data: {
        id: 7,
        ...payload,
      },
    })
    apiState.transactionApiClient.post.mockResolvedValueOnce({
      data: {
        id: 15,
        title: 'Camera',
      },
    })
    apiState.transactionApiClient.get.mockResolvedValueOnce({
      data: {
        id: 15,
        state: 'available',
      },
    })

    await expect(createProduct(payload)).resolves.toMatchObject({
      id: 7,
      transaction_product_id: 15,
    })
    await expect(getProductById(7)).resolves.toMatchObject({
      id: 7,
      transaction_product_id: 15,
    })

    expect(apiState.transactionApiClient.post).toHaveBeenCalledWith('/products/', {
      title: 'Camera',
      description: 'Good camera',
      category: 'Electronics',
      price: 120,
    })
    expect(apiState.transactionApiClient.get).toHaveBeenCalledWith('/products/15')
  })

  it('normalizes repeated condition filters for catalog requests', async () => {
    const { listProducts } = await import('@/services/product.service')

    apiState.inventoryApiClient.get.mockResolvedValueOnce({
      data: [],
    })

    await listProducts({
      category: 'Furniture',
      condition: ['Good', 'Poor'],
      maxPrice: '100',
      minPrice: '10',
    })

    expect(apiState.inventoryApiClient.get).toHaveBeenCalledWith(
      '/products',
      expect.objectContaining({
        params: {
          category: 'Furniture',
          condition: ['Good', 'Poor'],
          max_price: 100,
          min_price: 10,
        },
      }),
    )

    const requestConfig = apiState.inventoryApiClient.get.mock.calls[0][1]

    expect(requestConfig.paramsSerializer.serialize(requestConfig.params)).toBe(
      'category=Furniture&condition=Good&condition=Poor&min_price=10&max_price=100',
    )
  })

  it('uses the mapped transaction product ID for reserve, buy, and cancellation', async () => {
    const { buyProduct, cancelReservation, createProduct, reserveProduct } = await import(
      '@/services/product.service'
    )

    apiState.inventoryApiClient.post.mockResolvedValueOnce({
      data: {
        id: 7,
        title: 'Camera',
      },
    })
    apiState.transactionApiClient.post
      .mockResolvedValueOnce({
        data: {
          id: 15,
        },
      })
      .mockResolvedValueOnce({
        data: {
          state: 'reserved',
        },
      })
      .mockResolvedValueOnce({
        data: {
          status: 'completed',
        },
      })
      .mockResolvedValueOnce({
        data: {
          state: 'available',
        },
      })

    const product = await createProduct({
      title: 'Camera',
      description: 'Good camera',
      category: 'Electronics',
      price: 120,
    })

    await reserveProduct(product)
    await buyProduct(product)
    await cancelReservation(product)

    expect(apiState.transactionApiClient.post).toHaveBeenNthCalledWith(2, '/products/15/reserve')
    expect(apiState.transactionApiClient.post).toHaveBeenNthCalledWith(3, '/products/15/buy')
    expect(apiState.transactionApiClient.post).toHaveBeenNthCalledWith(
      4,
      '/products/15/cancel-reservation',
    )
  })

  it('syncs list state from the transaction product when a mapping exists', async () => {
    const { createProduct, listProducts } = await import('@/services/product.service')

    apiState.inventoryApiClient.post.mockResolvedValueOnce({
      data: {
        id: 7,
        title: 'Camera',
      },
    })
    apiState.transactionApiClient.post.mockResolvedValueOnce({
      data: {
        id: 15,
      },
    })
    apiState.inventoryApiClient.get.mockResolvedValueOnce({
      data: [
        {
          id: 7,
          title: 'Camera',
          state: 'Available',
          transaction_product_id: 15,
        },
      ],
    })
    apiState.transactionApiClient.get.mockResolvedValueOnce({
      data: {
        id: 15,
        state: 'reserved',
      },
    })

    await createProduct({
      title: 'Camera',
      description: 'Good camera',
      category: 'Electronics',
      price: 120,
    })

    await expect(listProducts()).resolves.toEqual([
      expect.objectContaining({
        id: 7,
        state: 'Reserved',
        transaction_product_id: 15,
      }),
    ])
  })

  it('treats an already reserved transition response as a reserved product', async () => {
    const { createProduct, reserveProduct } = await import('@/services/product.service')

    apiState.inventoryApiClient.post.mockResolvedValueOnce({
      data: {
        id: 7,
        title: 'Camera',
      },
    })
    apiState.transactionApiClient.post
      .mockResolvedValueOnce({
        data: {
          id: 15,
        },
      })
      .mockRejectedValueOnce({
        response: {
          status: 400,
          data: {
            detail:
              'Cannot transition from ProductState.RESERVED to ProductState.RESERVED',
          },
        },
      })

    const product = await createProduct({
      title: 'Camera',
      description: 'Good camera',
      category: 'Electronics',
      price: 120,
    })

    await expect(reserveProduct(product)).resolves.toMatchObject({
      product_id: 15,
      state: 'Reserved',
    })
  })

  it('rejects reserve when a listing has no transaction product mapping', async () => {
    const { reserveProduct } = await import('@/services/product.service')

    await expect(reserveProduct({ id: 7, title: 'Legacy listing' })).rejects.toThrow(
      'not connected to checkout',
    )
    expect(apiState.transactionApiClient.post).not.toHaveBeenCalled()
  })
})
